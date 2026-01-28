import socket
import json
import io
import struct
import time


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



def main():
    
    # Send TCP server the streaming start
    host ='192.168.10.55'
    port = 12345

    
    payload = {
        "text": "Hello Net Comm"
    }
    send_data_to_server(host, port, payload)
    
    # Wait for some time
    time.sleep(0.5)
    
    

    
if __name__ == "__main__":

    main()


