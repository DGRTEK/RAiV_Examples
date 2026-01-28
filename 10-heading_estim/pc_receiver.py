import socket
import json
import struct

def receive_data_from_client(host='192.168.10.2', port=12345):
    """
    Receives JSON data from a client over TCP socket
    
    Args:
        host (str): IP address to bind to (use '0.0.0.0' to accept from any interface)
        port (int): Port number to listen on
    """
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow reuse of address (helpful for quick restarts)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind to the specified address and port
            server_required = '0.0.0.0'  # Listen on all available interfaces
            server_socket.bind((server_required, port))
            
            # Listen for incoming connections (queue up to 5 connections)
            server_socket.listen(5)
            print(f"Server listening on {server_required}:{port}")
            
            while True:
                # Accept incoming connection
                conn, addr = server_socket.accept()
                print(f"Connection established with {addr}")
                
                try:
                    # Receive the 4-byte length header
                    length_bytes = b''
                    while len(length_bytes) < 4:
                        chunk = conn.recv(4 - len(length_bytes))
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
                        chunk = conn.recv(min(4096, remaining))
                        if not chunk:
                            raise ConnectionError("Connection closed by server while receiving data")
                        json_data += chunk
                        bytes_received += len(chunk)
    
                    if json_data:
                        payload = json.loads(json_data.decode('utf-8'))
                        print(f"Received payload: {payload}")
                        
                        # Process your payload here
                        if 'Heading' in payload:
                            print(f"  Heading:   {payload.get('Heading'):.2f}")
                        
                        # Optional: Send acknowledgment back to client
                        # response = {"status": "received", "message": "Data processed successfully"}
                        # client_socket.send(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                except Exception as e:
                    print(f"Error handling client {addr}: {e}")
                finally:
                    # Close the client connection
                    conn.close()
                    
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        except Exception as e:
            print(f"Server error: {e}")

if __name__ == "__main__":
    # Start the receiver
    receive_data_from_client()
