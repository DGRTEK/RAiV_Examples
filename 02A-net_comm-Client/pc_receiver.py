import socket
import struct
import json

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
                client_socket, client_address = server_socket.accept()
                print(f"Connection established with {client_address}")

                try:
                    # Simple protocol: send 4-byte length prefix + JSON payload
                    raw_len = client_socket.recv(4)
                    if len(raw_len) != 4:
                        continue
                    msg_len = struct.unpack('>I', raw_len)[0]
                    data = b''
                    while len(data) < msg_len:
                        chunk = client_socket.recv(msg_len - len(data))
                        if not chunk:
                            break
                        data += chunk
                    if len(data) != msg_len:
                        continue


                    if data:
                        # Decode bytes to string and parse JSON
                        payload = json.loads(data.decode('utf-8'))
                        print(f"Received payload: {payload}")

                        # Process your payload here
                        if 'text' in payload:
                            print(f"Message: {payload['text']}")

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                except Exception as e:
                    print(f"Error handling client {client_address}: {e}")
                finally:
                    # Close the client connection
                    client_socket.close()

        except KeyboardInterrupt:
            print("\nServer shutting down...")
        except Exception as e:
            print(f"Server error: {e}")

if __name__ == "__main__":
    # Start the receiver
    receive_data_from_client()
