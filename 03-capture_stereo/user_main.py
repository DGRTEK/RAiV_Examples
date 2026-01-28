import qCU_Net

# For accessing data pipeline
from qCU_Data import qCUData

# For creating reformating raw image pair
from helper_funcs import raw_to_bmp_bytes
import base64

import threading

def main():
    # Create data pipline interface
    theQCUData = qCUData()

    # Initialize the data pipeline interface
    if not theQCUData.init():
        print("Failed to initialize memory")
        return

    event = threading.Event()

    # Enter image acquisition loop
    try:
        while True:
            # Get Stereo Frame Data
            frame_data = theQCUData.getDataFrame()
            if frame_data is not None:
                if 'error' in frame_data:
                    print(f"Error occurred: {frame_data['error']}")
                else:
                    print("Acquired stereo frame")
                
                    # Get bmp from raw images
                    bmp_bytes_right = raw_to_bmp_bytes(frame_data[0], width=1600, height=1300, channels=3)
                    bmp_bytes_left = raw_to_bmp_bytes(frame_data[1], width=1600, height=1300, channels=3)
                    # Encode bmps to base64 strings
                    bmp_b64_right = base64.b64encode(bmp_bytes_right).decode('utf-8')
                    bmp_b64_left = base64.b64encode(bmp_bytes_left).decode('utf-8')
                    
                    # Build payload for the transmission
                    payload = {
                        "bmp_b64_right": bmp_b64_right,
                        "bmp_b64_left": bmp_b64_left
                    }
                    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

					# Do not forget to delete the frames
                    del frame_data
            else:
                # Wait to avoid high CPU utilization on idle
                event.wait(0.1)
                    
    finally:
        print("Loop Ended")


if __name__ == "__main__":
    main()
