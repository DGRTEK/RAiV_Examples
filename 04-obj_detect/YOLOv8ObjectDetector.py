import numpy as np
from typing import List, Dict, Any
import ctypes

class YOLOv8ObjectDetector:
    """YOLOv8 object detector for processing raw inference output."""
    
    
    def __init__(self, ai_classes: [], confidence_threshold: float = 0.5, iou_threshold: float = 0.45):
        """
        Initialize the YOLOv8 detector.
        
        Args:
            confidence_threshold: Minimum confidence score for detections (default: 0.5)
            iou_threshold: IoU threshold for non-maximum suppression (default: 0.45)
        """
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.classes = ai_classes;
    
    def detect_objects(self, ai_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract detected objects from YOLOv8 raw output data.
        
        Args:
            ai_data: Dictionary containing 'data' (float32 raw data) and 'header' 
            
        Returns:
            List of detected objects with format:
            [{'class_id': int, 'class_name': str, 'confidence': float, 
              'bbox': [x_center, y_center, width, height]}]
        """
        # Handle both list and bytes input for ai_data['data']
        data_input = ai_data['data']
            
        if hasattr(data_input, '_type_') and data_input._type_ == ctypes.c_float:
            # Handle ctypes pointer to c_float array (LP_c_float)
            # Get the total number of elements from header
            header = ai_data['header']
            total_elements = header.rows * header.cols
            # Create a ctypes array from the pointer and convert to numpy
            raw_data = np.ctypeslib.as_array(data_input, shape=(total_elements,)).astype(np.float32)
        elif isinstance(data_input, list):
            # Convert list of floats to numpy array directly
            raw_data = np.array(data_input, dtype=np.float32)
        elif isinstance(data_input, (bytes, bytearray)):
            # Convert bytes to numpy array with float32 dtype
            raw_data = np.frombuffer(data_input, dtype=np.float32)
        elif isinstance(data_input, np.ndarray):
            # Already a numpy array
            raw_data = data_input.astype(np.float32)
        else:
            raise TypeError(f"Unsupported data type for ai_data['data']: {type(data_input)}. "
                          f"Expected ctypes LP_c_float, list, bytes, bytearray, or numpy array.")
        
        # Get header information
        header = ai_data['header']
        rows = header.rows  # number of detections
        cols = header.cols  # features per detection
        
        # Reshape to proper detection format
        try:
            detections = raw_data.reshape(rows, cols)
        except ValueError as e:
            print(f"Error reshaping data: {e}")
            print(f"Expected shape: ({rows}, {cols}), actual data size: {len(raw_data)}")
            return []
        
        #print(f"{raw_data.shape} - {rows} - {cols}")
        
        #print(f"{detections[:, 0]}")
        
        # This is YoloV8 detections and they are transposed to match YoloV5
        detections = detections.T
        
        # Extract bounding box coordinates and class probabilities
        bboxes = detections[:, :4]
        class_scores = detections[:, 4:]
        
        # Get the maximum class score and corresponding class ID for each detection
        max_class_scores = np.max(class_scores, axis=1)
        class_ids = np.argmax(class_scores, axis=1)
        
        # Filter detections by confidence threshold
        valid_detections = max_class_scores >= self.confidence_threshold
        
        if not np.any(valid_detections):
            return []
        
        # Apply filtering
        filtered_bboxes = bboxes[valid_detections]
        filtered_scores = max_class_scores[valid_detections]
        filtered_class_ids = class_ids[valid_detections]
        
        # Apply Non-Maximum Suppression
        keep_indices = self._nms(filtered_bboxes, filtered_scores, self.iou_threshold)
        
        # Create result list
        detected_objects = []
        for idx in keep_indices:
            class_id = int(filtered_class_ids[idx])
            confidence = float(filtered_scores[idx])
            bbox = filtered_bboxes[idx].tolist()
            
            # Ensure class_id is within valid range
            if class_id < len(self.classes):
                class_name = self.classes[class_id]
            else:
                class_name = f"unknown_class_{class_id}"
            
            detected_objects.append({
                'class_id': class_id,
                'class_name': class_name,
                'confidence': confidence,
                'bbox': bbox  # [x_center, y_center, width, height]
            })
        
        return detected_objects
    
    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
        """
        Non-Maximum Suppression implementation.
        
        Args:
            boxes: Array of bounding boxes in format [x_center, y_center, width, height]
            scores: Array of confidence scores
            iou_threshold: IoU threshold for suppression
        
        Returns:
            List of indices to keep
        """
        if len(boxes) == 0:
            return []
        
        # Convert from [x_center, y_center, width, height] to [x1, y1, x2, y2]
        x1 = boxes[:, 0] - boxes[:, 2] / 2
        y1 = boxes[:, 1] - boxes[:, 3] / 2
        x2 = boxes[:, 0] + boxes[:, 2] / 2
        y2 = boxes[:, 1] + boxes[:, 3] / 2
        
        # Calculate areas
        areas = (x2 - x1) * (y2 - y1)
        
        # Sort by scores in descending order
        order = scores.argsort()[::-1]
        keep = []
        
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
                
            # Calculate IoU
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            intersection = w * h
            
            iou = intersection / (areas[i] + areas[order[1:]] - intersection)
            
            # Keep boxes with IoU less than threshold
            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        
        return keep
    
    def set_thresholds(self, confidence_threshold: float = None, iou_threshold: float = None):
        """Update detection thresholds."""
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        if iou_threshold is not None:
            self.iou_threshold = iou_threshold



    def yolo_to_coords_float(self, inAiPrepro, yolo_bbox):
        
        
        cropX = inAiPrepro.cropX
        cropY = inAiPrepro.cropY
        procWidth = inAiPrepro.procWidth
        procHeight = inAiPrepro.procHeight
        imWidth = inAiPrepro.cropWidth +inAiPrepro.cropX*2;
        imHeight = inAiPrepro.cropHeight +inAiPrepro.cropY*2;
        
        offsetX = 0
        offsetY = 0;
        imageCoef = 0;
        if (imWidth/imHeight > procWidth/procHeight):
            # Image is wider than desired - crop width
            imageCoef = imHeight/procHeight
            offsetX = (imWidth-imageCoef*procWidth)/2;
        else:
            # Image is taller than desired - crop height
            imageCoef = imWidth/procWidth
            offsetY = (imHeight-imageCoef*procHeight)/2;
        
        #print(f"{imWidth} x {imHeight} - {procWidth} x {procHeight}")
        #print(f"{imageCoef} - {offsetX} - {offsetY}")
        
        """Same as above but returns float values instead of integers."""
        center_x, center_y, width, height = yolo_bbox
        
        center_x *= procWidth
        center_y *= procHeight
        width *= procWidth
        height *= procHeight
        
        center_x = center_x*imageCoef +offsetX
        center_y = center_y*imageCoef +offsetY
        width = width*imageCoef
        height = height*imageCoef
        
        x_min = center_x - width / 2
        y_min = center_y - height / 2
        x_max = center_x + width / 2
        y_max = center_y + height / 2
        
        # Make the box stay inside the image
        x_min = max(0, min(x_min, imWidth-1))
        y_min = max(0, min(y_min, imHeight-1))
        x_max = max(0, min(x_max, imWidth-1))
        y_max = max(0, min(y_max, imHeight-1))
        
        return [x_min, y_min, x_max-x_min, y_max-y_min]

    def get_center_degree(self, inAiPrepro, imageRect, lensHFov, lensVFov):
        
        cropX = inAiPrepro.cropX
        cropY = inAiPrepro.cropY
        imWidth = inAiPrepro.cropWidth +inAiPrepro.cropX*2;
        imHeight = inAiPrepro.cropHeight +inAiPrepro.cropY*2;
        
        x_ctr = imageRect[0]+imageRect[2]/2;
        y_ctr = imageRect[1]+imageRect[3]/2;
        
        degPix_hRatio = lensHFov/imWidth;
        degPix_vRatio = lensVFov/imHeight;
        
        x_ctr_deg = (x_ctr-imWidth/2)*degPix_hRatio;
        y_ctr_deg = (y_ctr-imHeight/2)*degPix_vRatio;
        
        return [x_ctr_deg, y_ctr_deg];
    