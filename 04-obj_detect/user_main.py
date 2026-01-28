import qCU_Print
import qCU_Net
# Object Detection
from qCU_Data import qCUData
from YOLOv8ObjectDetector import YOLOv8ObjectDetector

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

                    # Postprocess the ai_data
                    detected_objects = objDetector.detect_objects(ai_data)

                    #print(detected_objects)

                    end_time = time.perf_counter()

                    execution_time = end_time - start_time
                    execTime.append(execution_time)

                    
                    # Get the image ai preprocessing parameters
                    aiHeader = ai_data['header']
                    aiPrepro = aiHeader.imPreproPrms

                    detected_objs_image = []
                    for obj in detected_objects:

                        # Convert yolo coordinates to image coordinates
                        bbox_img_float = objDetector.yolo_to_coords_float(aiPrepro, obj['bbox'])
                        bbox_img_int = [int(coord) for coord in bbox_img_float]

                        detected_objs_image.append({
                            'class_id': obj['class_id'],
                            'class_name': obj['class_name'],
                            'confidence': obj['confidence'],
                            'bbox': bbox_img_int,
                        })

                    print(detected_objs_image)

                    # Get bmp from  raw image
                    bmp_bytes = raw_to_bmp_bytes(ai_data['input_frame_right'], width=1600, height=1300, channels=3)
                    # Encode image to base64 string
                    bmp_b64 = base64.b64encode(bmp_bytes).decode('utf-8')
                    # Build payload for the transmission
                    payload = {
                        "image_bmp_b64": bmp_b64,
                        "detected_objects": detected_objs_image
                    }
                    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)
                    

                    # Print timing on every 5 NPU outputs
                    if counter >= 5:
                        # Print execution time statistics
                        print(f"obj: min={min(execTime):.3f}s, max={max(execTime):.3f}s, avg={sum(execTime) / len(execTime):.3f}s, count={len(execTime)}")

                        # Reset execution timer
                        execTime = []
                        counter = 0
                    else:
                        counter += 1
                    
                    
                    del ai_data['data'], ai_data['input_frame_right'], ai_data['input_frame_left'], ai_data['header']
                    del ai_data
            else:
                # Wait to avoid high CPU utilization
                time.sleep(0.1)
                    
                    
    #except Exception as e:  # Catches ALL built-in exceptions (except BaseException)
    #    print(f"An error occurred: {e}")
    finally:
        print("Cleanup completed")


if __name__ == "__main__":
    main()
