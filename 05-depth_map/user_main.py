import qCU_Print
import qCU_Net
# Depth Estimation
from qCU_Data import qCUData
from StereoDepthEstimator import StereoDepthEstimator
import depthUtils


import time

# For sending data over TCP
import base64



def main():

    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    print("**** Depth Map Example ****")

    # Create interface
    theQCUData = qCUData()

    # Initialize shared memory
    if not theQCUData.init():
        print("Failed to initialize shared memory")
        return

    # Get memory configuration of the data
    memConfig = theQCUData.getMemoryConfiguration()

    # Initialize OpenCV's depth estimation algorithms
    depthScale = 0.5
    depthMinMM = 250 #350.0
    depthMaxMM = 600 #750#5500.0
    depthEstimator = StereoDepthEstimator(
        scale_factor=depthScale,
        # The depth values are in milimeters ("mm")
        min_depth=depthMinMM,
        max_depth=depthMaxMM,
    )

    '''
    # Generate ground depth plane (for obstacle detection if needed)
    P1 = depthEstimator.P1
    num_disp = depthEstimator.sgbm_params['numDisparities']
    imWidth = 726
    imHeight = 585
    CAMERA_SPECS = {
        "image_width": imWidth,
        "image_height": imHeight,
        'fx': P1[0, 0],  # focal length x
        'fy': P1[1, 1],  # focal length y
        'cx': P1[0, 2],  # principal point x
        'cy': P1[1, 2],   # principal point y
        "camera_height_mm": 170.0
    }
    depth_map_horizontal = depthUtils.generate_ground_plane_depth_map_from_intrinsics(
        **CAMERA_SPECS,
        # Calibrate setup pitch by using calibration pattern
        camera_pitch_deg= -5.0 #0.0
    )
    '''


    # Paramters for execution timing statistics
    execTime = []
    counter = 0

    # Enter object detection loop
    try:
        while True:
            # Get Ai data
            ai_data = theQCUData.getDataAi()
            if ai_data:
                if 'error' in ai_data:
                    print(f"Error occurred: {ai_data['error']}")
                else:

                    start_time = time.perf_counter()

                    # NOTE: 1. We are processing AI output images. Stereo camera output can also be processed
                    #       2. Due to the stereo camera setup the output depth map size is 726x585

                    # Process Ai processor output images
                    depthMap = depthUtils.getDepthFromStereo(ai_data, memConfig, depthEstimator)

                    end_time = time.perf_counter()

                    execution_time = end_time - start_time
                    execTime.append(execution_time)

                    # Get colored depth map
                    coloredDepthMap = depthEstimator.depth_to_colormap(depthMap)
                    coloredDepthMap_b64 = base64.b64encode(coloredDepthMap).decode('utf-8')
                    # Build payload for the transmission
                    payload = {
                        "width": 726,
                        "height": 585,
                        "depth": coloredDepthMap_b64,
                    }
                    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

                    print("data sent")

                    # Print timing on every 5 NPU outputs
                    if counter >= 5:
                        # Print execution time statistics
                        print(f"depth: min={min(execTime):.3f}s, max={max(execTime):.3f}s, avg={sum(execTime) / len(execTime):.3f}s, count={len(execTime)}")

                        counter = 0
                    else:
                        counter += 1
            else:
                # Wait to avoid high CPU utilization
                time.sleep(0.1)
                    

    except Exception as e:  # Catches ALL built-in exceptions (except BaseException)
        print(f"An error occurred: {e}")
    finally:
        print("Cleanup completed")


if __name__ == "__main__":
    main()
