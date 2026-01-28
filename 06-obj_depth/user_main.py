import qCU_Print
import qCU_Net
# Object Detection
from qCU_Data import qCUData
from YOLOv8ObjectDetector import YOLOv8ObjectDetector
# Depth Estimation
from StereoDepthEstimator import StereoDepthEstimator
import depthUtils


import time

# For sending data over TCP
from helper_funcs import raw_to_bmp_bytes
import base64



def main():


    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    print("**** Object Detection Example ****")

    # Create interface
    theQCUData = qCUData()

    # Initialize shared memory
    if not theQCUData.init():
        print("Failed to initialize shared memory")
        return



    # Initialize COCO classes
    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush"
    ]

    # Initialize Yolo detector post processor
    objDetector = YOLOv8ObjectDetector(ai_classes=COCO_CLASSES, confidence_threshold=0.25, iou_threshold=0.45)


    # Get memory configuration of the data
    memConfig = theQCUData.getMemoryConfiguration()

    # Initialize OpenCV's depth estimation algorithms
    depthScale = 0.5
    depthMinMM = 250 #50.0
    depthMaxMM = 650 #5500.0
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
    execTime_obj = []
    execTime_depth = []
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

                    # Postprocess the ai_data
                    detected_objects = objDetector.detect_objects(ai_data)

                    end_time = time.perf_counter()

                    execution_time = end_time - start_time
                    execTime_obj.append(execution_time)



                    start_time = time.perf_counter()

                    # NOTE: 1. We are processing AI output images. Stereo camera output can also be processed
                    #       2. Due to the stereo camera setup the output depth map size is 726x585

                    # Process Ai processor output images
                    depthMap = depthUtils.getDepthFromStereo(ai_data, memConfig, depthEstimator)

                    end_time = time.perf_counter()

                    execution_time = end_time - start_time
                    execTime_depth.append(execution_time)

                    # Get the image ai preprocessing parameters
                    aiHeader = ai_data['header']
                    aiPrepro = aiHeader.imPreproPrms

                    detected_objsNDepth_image = []
                    for obj in detected_objects:

                        # Convert yolo coordinates to image coordinates
                        bbox_img_float = objDetector.yolo_to_coords_float(aiPrepro, obj['bbox'])
                        bbox_img_int = [int(coord) for coord in bbox_img_float]

                        # For lens EFL 2.8mm
                        lensHFov = 81.20; # degrees
                        lensVFov = 69.71; # degrees
                        ctrDirectionDegrees = objDetector.get_center_degree(aiPrepro, bbox_img_float, lensHFov, lensVFov)

                        # Get depth of the object
                        obj_depth_min, obj_depth_max, obj_depth_median = depthEstimator.get_depth_of_rect(depthMap, bbox_img_int)
                        detected_objsNDepth_image.append({
                            'class_id': obj['class_id'],
                            'class_name': obj['class_name'],
                            'confidence': obj['confidence'],
                            'bbox': bbox_img_int,
                            'depth_min': float(obj_depth_min),
                            'depth_max': float(obj_depth_max),
                            'depth_med': float(obj_depth_median),
                            'ctrDirectDeg': ctrDirectionDegrees
                        })



                    # Get bmp from  raw image
                    bmp_bytes = raw_to_bmp_bytes(ai_data['input_frame_right'], width=1600, height=1300, channels=3)
                    # Encode image to base64 string
                    bmp_b64 = base64.b64encode(bmp_bytes).decode('utf-8')
                    # Build payload for the transmission
                    payload = {
                        "image_bmp_b64": bmp_b64,
                        "detected_objects": detected_objsNDepth_image
                    }
                    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)


                    # Print timing on every 5 NPU outputs
                    if counter >= 5:
                        # Print execution time statistics
                        print(f"obj: min={min(execTime_obj):.3f}s, max={max(execTime_obj):.3f}s, avg={sum(execTime_obj) / len(execTime_obj):.3f}s, count={len(execTime_obj)}")
                        print(f"depth: min={min(execTime_depth):.3f}s, max={max(execTime_depth):.3f}s, avg={sum(execTime_depth) / len(execTime_depth):.3f}s, count={len(execTime_depth)}")

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
