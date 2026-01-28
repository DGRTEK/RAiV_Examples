import socket
import json
import io
import struct
import time
from pc_liveWsH264 import liveWsH264
import time


import tkinter as tk
from PIL import Image, ImageTk
import threading


IMAGE_WIDTH = 1600
IMAGE_HEIGHT = 1300

CANVAS_SCALE = 0.5
CANVAS_WIDTH = int(IMAGE_WIDTH*CANVAS_SCALE);
CANVAS_HEIGHT = int(IMAGE_HEIGHT*CANVAS_SCALE);


def send_data_to_server(host, port, json_payload, receive_handler=None, receive_timeout=5.0):
    """
    Sends a JSON-encoded payload to a server over TCP and optionally handles a response.
    
    Args:
        host (str): The server's IP address or hostname.
        port (int): The server's port number.
        json_payload (dict): The dictionary to be JSON-encoded and sent.
        receive_handler (callable, optional): Function to handle received response data.
            Should accept a single argument (dict) containing the JSON response.
        receive_timeout (float, optional): Timeout in seconds for waiting for response.
            Default is 5.0 seconds.
            
    Returns:
        bool: True if send was successful, False otherwise.
        If receive_handler is provided, returns True only if both send and receive
        operations complete successfully.
    """
    try:
        # Serialize the dictionary to a JSON formatted string
        json_string = json.dumps(json_payload)
        
        # Encode the JSON string into bytes for transmission (UTF-8 is standard)
        message_bytes = json_string.encode('utf-8')

        # Create a socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to the server
            s.connect((host, port))
            print(f"Connected to {host}:{port}")
            
            # Send the length of the data first (4-byte unsigned int, network byte order)
            length = len(message_bytes)
            s.sendall(struct.pack('!I', length))
            
            # Send the actual JSON data
            s.sendall(message_bytes)
            print(f"Sent {len(message_bytes)} bytes of JSON data.")
            
            # If a receive handler is provided, wait for and process the response
            if receive_handler is not None:
                # Set socket timeout for receiving
                s.settimeout(receive_timeout)
                
                try:
                    # Receive the 4-byte length header
                    length_bytes = b''
                    while len(length_bytes) < 4:
                        chunk = s.recv(4 - len(length_bytes))
                        if not chunk:
                            raise ConnectionError("Connection closed by server while receiving length header")
                        length_bytes += chunk
                    
                    # Unpack the length (network byte order)
                    message_length = struct.unpack('!I', length_bytes)[0]
                    print(f"Expected response length: {message_length} bytes")
                    
                    # Receive the actual JSON data
                    json_data = b''
                    bytes_received = 0
                    while bytes_received < message_length:
                        remaining = message_length - bytes_received
                        chunk = s.recv(min(4096, remaining))
                        if not chunk:
                            raise ConnectionError("Connection closed by server while receiving data")
                        json_data += chunk
                        bytes_received += len(chunk)
                    
                    print(f"Received {len(json_data)} bytes of JSON response")
                    
                    # Decode and parse JSON
                    json_string = json_data.decode('utf-8')
                    json_response = json.loads(json_string)
                    
                    # Call the receive handler with the parsed response
                    return receive_handler(json_response)
                    
                except socket.timeout:
                    print(f"Timeout waiting for response from server (timeout: {receive_timeout}s)")
                    return False
                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON response: {e}")
                    return False
                except struct.error as e:
                    print(f"Failed to unpack message length: {e}")
                    return False
                except ConnectionError as e:
                    print(f"Connection error while receiving response: {e}")
                    return False
            
            return True
            
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {host}:{port}?")
    except socket.timeout:
        print(f"Connection timeout while connecting to {host}:{port}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return False







class TkinterVideoPlayer:
    def __init__(self, root, ws_url):
        
        self.wsH264 = liveWsH264(ws_url)
        
        # Start WebSocket connection
        self.ws_thread = self.wsH264.start()
        
        time.sleep(1.5)
    
        self.root = root
        self.root.title("Live Stream")
        
        # Create video label
        self.video_label = tk.Label(root)
        self.video_label.pack()
                
        # Control flags
        self.running = True
        #self.current_image = None
        
    def update_frame(self, frame):
        """Update the displayed frame"""
        # Convert frame to PIL Image
        img_array = frame.to_ndarray(format='rgb24')
        img_pil = Image.fromarray(img_array)
        
        # Resize if needed (optional safety)
        if img_pil.size != (CANVAS_WIDTH, CANVAS_HEIGHT):
            img_pil = img_pil.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.LANCZOS)
        
        
        # Convert to PhotoImage (Tkinter format)
        #self.current_image = ImageTk.PhotoImage(img_pil)
        #self.video_label.configure(image=self.current_image)
        
        current_image = ImageTk.PhotoImage(img_pil)
        self.video_label.configure(image=current_image)
        self.video_label.image = current_image
        
    def play_stream(self):
        """Main playback loop"""
        
        try:
            # Process decoded frames
            while self.wsH264.running:
                frame = self.wsH264.get_frame(timeout=1.0)
                if frame:
                    # Process your frame here
                    print(f"Got frame: {frame.width}x{frame.height}, format: {frame.format}")
                    
                    self.update_frame(frame)
                    
                    '''
                    # Flush frames
                    while frame:
                        frame = self.wsH264.get_frame(timeout=0.0)
                    '''
                    
                    
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            self.wsH264.stop()
            self.root.quit()
        
        '''
        try:
            for packet in packet_source:
                if not self.running:
                    break
                    
                frames = self.codec.decode(packet)
                for frame in frames:
                    if not self.running:
                        break
                    self.update_frame(frame)
                    
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            self.root.quit()
        '''
    
    def start_playback(self):
        """Start playback in a separate thread"""
        playback_thread = threading.Thread(
            target=self.play_stream,
            daemon=True
        )
        playback_thread.start()
        
    def stop(self):
        self.running = False




def main():
    

    # Send TCP server the streaming start
    host ='192.168.10.55'
    port = 12345

    # Built in websocket runs at port "8081"
    ws_url = "ws://"+host+':8081'    
    
    payload = {
    "live_isStart": 1,
    "live_isStereo": 0
    }
    send_data_to_server(host, port, payload)
    
    # Wait for some time
    time.sleep(0.5)
    

    
    # Create and run
    root = tk.Tk()

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate position
    x = (screen_width // 2) - (CANVAS_WIDTH // 2)
    y = (screen_height // 2) - (CANVAS_HEIGHT // 2)

    # Set initial window size and position
    root.geometry(f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}+{x}+{y}")
    
    player = TkinterVideoPlayer(root, ws_url)
    player.start_playback()
    
    # Handle window close
    def on_closing():
        player.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
    
    
    # Disable streaming
    payload = {
        "live_isStart": 0,
        "live_isStereo": 0
    }
    send_data_to_server(host, port, payload)
    

    
if __name__ == "__main__":

    main()


