import av
import av.error
from queue import Queue
import websocket
import threading
import datetime

import queue

class liveWsH264:
    def __init__(self, ws_url, record=False):
        self.ws_url = ws_url
        self.codec = av.CodecContext.create('h264', 'r')
        self.frame_queue = Queue()
        self.running = False
        self.ws = None
        
        # Store parameter sets
        self.sps = None
        self.pps = None
        self.configured = False
        
        self.record = record

        if self.record:
            
            current_time = datetime.datetime.now()
            output_filename = current_time.strftime("rec_%Y%m%d_%H%M%S.mp4")
            
            self.codec = av.CodecContext.create('h264', 'r')
            self.frame_queue = queue.Queue()
            
            # Setup output file
            self.output_container = av.open(output_filename, mode='w')
            self.output_stream = self.output_container.add_stream('h264')
            # Explicitly set resolution and other properties (match your input)
            self.output_stream.width = 1600
            self.output_stream.height = 1300            
            # Optional but recommended: set pixel format (e.g., 'yuv420p' for broad compatibility)
            self.output_stream.pix_fmt = 'yuv420p'
            # Set time_base (e.g., if your input is 30 fps)
            #self.output_stream.time_base = fractions.Fraction(1, 30)  # or use your actual frame rate
            # Optionally set framerate (some containers/codecs care)
            self.output_stream.rate = 30  # frames per second
        
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages containing H.264 data"""
        try:
            # message is already bytes in Python websocket-client
            data = message
            
            # Parse multiple NAL units from the message
            nal_units = self.parse_nal_units(data)
            
            for nal_unit in nal_units:
                nal_type = self.get_nal_type(nal_unit)
                nal_types = {
                    1: "Non-IDR", 
                    5: "IDR", 
                    6: "SEI", 
                    7: "SPS", 
                    8: "PPS",
                    9: "AUD"
                }
                print(f"NAL unit type: {nal_type} ({nal_types.get(nal_type, 'Unknown')})")
                
                # Handle different NAL unit types
                if nal_type == 7:  # SPS
                    self.sps = nal_unit
                    print("Stored SPS")
                elif nal_type == 8:  # PPS
                    self.pps = nal_unit
                    print("Stored PPS")
                elif nal_type in [1, 5]:  # Non-IDR or IDR frame
                    self.decode_frame_data(nal_unit, nal_type)
                elif nal_type == 6:  # SEI
                    print("Received SEI (supplemental enhancement information)")
                else:
                    print(f"Skipping NAL unit type {nal_type}")
                    
        except Exception as e:
            print(f"ERROR: Error processing message: {e}")
    
    def parse_nal_units(self, data):
        """Parse multiple NAL units from H.264 data"""
        nal_units = []
        start = 0
        
        while start < len(data):
            # Find start code
            start_code_pos = self.find_start_code(data, start)
            if start_code_pos == -1:
                break
                
            # Find next start code to determine NAL unit length
            next_start_code = self.find_start_code(data, start_code_pos + 4)
            
            if next_start_code == -1:
                # This is the last NAL unit
                nal_unit = data[start_code_pos:]
            else:
                # Extract NAL unit up to next start code
                nal_unit = data[start_code_pos:next_start_code]
            
            if len(nal_unit) > 4:  # Must have at least start code + 1 byte
                nal_units.append(nal_unit)
            
            start = next_start_code if next_start_code != -1 else len(data)
        
        return nal_units
    
    def find_start_code(self, data, start_pos=0):
        """Find H.264 start code (0x00000001 or 0x000001) starting from start_pos"""
        for i in range(start_pos, len(data) - 3):
            if data[i:i+4] == b'\x00\x00\x00\x01':
                return i
            elif data[i:i+3] == b'\x00\x00\x01':
                return i
        return -1
    
    def get_nal_type(self, data):
        """Extract NAL unit type from H.264 data"""
        if len(data) >= 5:
            # Check for start code (0x00000001 or 0x000001)
            if data[:4] == b'\x00\x00\x00\x01':
                nal_byte = data[4]
            elif len(data) >= 4 and data[:3] == b'\x00\x00\x01':
                nal_byte = data[3]
            else:
                # No start code found, assume first byte is NAL header
                nal_byte = data[0] if data else 0
        else:
            nal_byte = data[0] if data else 0
            
        return nal_byte & 0x1F
    
    def decode_frame_data(self, frame_data, nal_type):
        """Decode actual frame data (IDR or Non-IDR)"""
        if not frame_data:
            return
        
        # For IDR frames or if codec isn't configured, prepend SPS/PPS
        if nal_type == 5 or not self.configured:  # IDR frame or first frame
            if not self.sps or not self.pps:
                print("WARN: Cannot decode frame - missing SPS or PPS")
                return
                
            # Create complete packet with SPS + PPS + Frame
            complete_data = self.sps + self.pps + frame_data
            self.configured = True
            print("Created complete packet with SPS + PPS + Frame")
        else:
            # For Non-IDR frames after configuration, just use frame data
            complete_data = frame_data
            
        self.decode_h264_data(complete_data)
    
    def decode_h264_data(self, h264_data):
        """Decode H.264 data and store frames"""
        if not h264_data:
            return
            
        try:
            # Create packet from raw H.264 data
            packet = av.Packet(h264_data)
            
            '''
            # Save to MP4 file if output is configured
            if self.output_container and self.output_stream:
                # Create a new packet for output (don't modify the original)
                output_packet = av.Packet(h264_data)
                # Set timestamp if needed (you might need to track frame timing)
                output_packet.stream = self.output_stream
                self.output_container.mux(output_packet)
            '''
            
            
            # Decode packet
            frames = self.codec.decode(packet)
            
            # Store decoded frames
            for frame in frames:
                self.frame_queue.put(frame)
                print(f"Decoded frame: {frame.width}x{frame.height}")
                
            if self.record:
                # Encode and write frames to output file
                for frame in frames:
                    for packet in self.output_stream.encode(frame):
                        self.output_container.mux(packet)
                    
        except (av.error.InvalidDataError, av.error.FFmpegError) as e:
            print(f"WARN: AV decoding error: {e}")
        except Exception as e:
            print(f"ERROR: Unexpected decoding error: {e}")
    
    def get_frame(self, timeout=None):
        """Get next decoded frame from queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except:
            return None
    
    def on_error(self, ws, error):
        print(f"ERROR: WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket connection closed")
        '''
        """Properly close the output container"""
        if self.output_container:
            try:
                # Flush any remaining frames
                if self.output_stream:
                    for packet in self.output_stream.encode(None):
                        self.output_container.mux(packet)
                self.output_container.close()
                print(f"MP4 file saved: {self.output_filename}")
            except Exception as e:
                print(f"ERROR: Failed to close output container: {e}")
        '''
        self.running = False
    
    def on_open(self, ws):
        print(f"WebSocket connection opened")
        self.running = True
        '''
        if self.record:
            # Format the timestamp as YYYYMMDD_HHMMSS
            current_time = datetime.datetime.now()
            output_filename = current_time.strftime("rec_%Y%m%d_%H%M%S.mp4")
            # MP4 output setup
            self.output_container = None
            self.output_stream = None
            self.output_filename = output_filename
            
            if output_filename:
                """Initialize MP4 output container"""
                try:
                    self.output_container = av.open(self.output_filename, 'w')
                    self.output_stream = self.output_container.add_stream('h264')
                    # You can set codec parameters here if needed
                    # self.output_stream.pix_fmt = 'yuv420p'
                except Exception as e:
                    print(f"ERROR: Failed to create output container: {e}")
        '''
    def start(self):
        """Start WebSocket connection in a separate thread"""
        def run():
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.ws.run_forever()
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop(self):
        """Stop the WebSocket connection"""
        self.running = False
        if self.ws:
            self.ws.close()
        
        """Close the output file properly"""
        if hasattr(self, 'output_container'):
            # Flush the encoder
            for packet in self.output_stream.encode():
                self.output_container.mux(packet)
            self.output_container.close()
