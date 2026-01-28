import qCU_Print
import qCU_Net
from qCU_Data import qCUData
from headingEstim import HeadingEstimator
from headingEstim import estimate_IMU_bias

import threading

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

    event = threading.Event()

    # Get gyro and accelerator biases
    maxCount = 200
    accel_bias, gyro_bias = estimate_IMU_bias(theQCUData, maxCount)

    # Start heading estimator thread
    headingEstimator = HeadingEstimator(theQCUData=theQCUData, gyro_bias=gyro_bias)
    headingEstimator.start()


    # Enter object detection loop
    try:
        # Main loop to get data
        loop_count = 0
        max_loops = 500  # Limit for demonstration

        while loop_count < max_loops:
            curHeading = headingEstimator.get_heading()

            print(f"Heading: {curHeading:.3f}");
            payload = {
                "Heading": curHeading
            }
            qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

            # Sleep 1 seconds
            event.wait(1.0)

    #except Exception as e:  # Catches ALL built-in exceptions (except BaseException)
    #    print(f"An error occurred: {e}")
    finally:
        print("Cleanup completed")


    # Stop heading estimator
    headingEstimator.stop()


if __name__ == "__main__":
    main()
