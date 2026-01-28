import socket
import json

def start_imu_server(host='192.168.10.2', port=12345):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"📡 Listening for IMU data on {host}:{port}...")

        while True:
            conn, addr = server_socket.accept()
            print(f"✅ Connection from {addr}")

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
                    imu_data = payload.get("IMU", {})

                    print("\n📦 Received IMU Data:")
                    print(f"  Accel (g):   X={imu_data.get('accel_x'):.3f}, "
                          f"Y={imu_data.get('accel_y'):.3f}, Z={imu_data.get('accel_z'):.3f}")
                    print(f"  Gyro (dps):  X={imu_data.get('gyro_x'):.2f}, "
                          f"Y={imu_data.get('gyro_y'):.2f}, Z={imu_data.get('gyro_z'):.2f}")
                    print(f"  Temp (°C?):  {imu_data.get('temp'):.2f}")
                    print(f"  FSYNC ago:   {imu_data.get('fsyncAgo')}")
                    print(f"  Timestamp:   {imu_data.get('timestamp'):.6f}")
                    print("-" * 50)

            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
            except Exception as e:
                print(f"⚠️ Error handling connection: {e}")
            finally:
                conn.close()

if __name__ == "__main__":
    start_imu_server()
