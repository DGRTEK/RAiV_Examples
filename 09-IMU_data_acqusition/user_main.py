import qCU_Print
import qCU_Net
from qCU_Data import qCUData

def main():

    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    print("**** Net Comm Example ****")


    # Create interface
    theQCUData = qCUData()

    # Initialize shared memory
    if not theQCUData.init():
        print("Failed to initialize shared memory")
        return


    last_imu_index = None

    # Enter object detection loop
    try:
        # Main loop to get data
        loop_count = 0
        max_loops = 100  # Limit for demonstration

        while loop_count < max_loops:

            # Get the raw IMU data and print
            raw_imu_data, current_imu_index = theQCUData.getDataRawImu()
            # Process data only when the index changes (new data available)
            if last_imu_index is not None and current_imu_index != last_imu_index:
                print(f"Received {len(raw_imu_data)} raw IMU samples")
                print(f"  IMU Raw: {raw_imu_data}")

                payload = {
                    "IMU": raw_imu_data
                }
                qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

                # Increment loop count
                loop_count += 1

            last_imu_index = current_imu_index

    except Exception as e:  # Catches ALL built-in exceptions (except BaseException)
        print(f"An error occurred: {e}")
    finally:
        print("Cleanup completed")

    payload = {
        "text": "Hello Net Comm"
    }
    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

if __name__ == "__main__":
    main()
