import cv2 as cv
import numpy as np



def getDepthFromStereo(ai_data, config, estimator):
    # Get stereo pair
    left_raw_image = np.frombuffer(ai_data['input_frame_left'], dtype=np.uint8)
    right_raw_image = np.frombuffer(ai_data['input_frame_right'], dtype=np.uint8)
    #
    width = config['frame_width']
    height = config['frame_height']
    bpp = config['frame_bpp']
    left_image = reshape_raster(left_raw_image, width, height, bpp)
    right_image = reshape_raster(right_raw_image, width, height, bpp)
    
    depthMap = estimator.process_pair_from_raster(
        imgL_rgb=left_image,
        imgR_rgb=right_image
    )
    return depthMap


def reshape_raster(raster_data: np.ndarray, width, height, bpp) -> np.ndarray:
    """
    Convert (H*W*3, 1) or (H*W*3,) raster RGB data to (H, W, 3) RGB image.
    """
    expected_size = width*height*bpp
    flat = np.asarray(raster_data).flatten()

    if flat.size != expected_size:
        raise ValueError(
            f"Raster data size {flat.size} doesn't match expected {expected_size} "
            f"for image shape ({self.orig_h}, {self.orig_w})"
        )

    # Reshape to (H, W, 3) in RGB order
    rgb_image = flat.reshape((height, width, bpp))
    bgr_image = cv.cvtColor(rgb_image, cv.COLOR_RGB2BGR)
    return bgr_image.astype(np.uint8)



def unrectified_to_rectified_coords_pmatrix(points, K, D, P):
    """
    Convert using the full projection matrix from stereoRectify.
    
    Parameters:
    - points: Nx2 array of (x, y) coordinates
    - K: Original camera matrix
    - D: Distortion coefficients  
    - P: Projection matrix from stereoRectify (P1 for left, P2 for right)
    
    Returns:
    - rectified_points: Nx2 array of rectified coordinates
    """
    points_reshaped = points.reshape(-1, 1, 2).astype(np.float32)
    
    # Undistort to normalized coordinates
    undistorted_norm = cv.undistortPoints(points_reshaped, K, D)
    
    # Convert to homogeneous 3D rays
    rays = np.hstack([undistorted_norm.reshape(-1, 2), np.ones((len(points), 1))])
    
    # Apply projection matrix
    projected = rays @ P[:, :3].T + P[:, 3:].T
    rectified_points = projected[:, :2] / projected[:, 2:]
    
    return rectified_points



def rectified_to_unrectified_coords(points_rect, K, D, R_rect, P):
    """
    Convert rectified image coordinates back to unrectified coordinates.
    
    Parameters:
    - points_rect: Nx2 array of (x, y) rectified coordinates.
    - K: Original camera matrix.
    - D: Distortion coefficients.
    - R_rect: Rectification rotation matrix (R1 or R2 from stereoRectify).
    - P: Projection matrix from stereoRectify (P1 or P2).
    
    Returns:
    - unrectified_points: Nx2 array of unrectified coordinates.
    """
    points_rect = np.asarray(points_rect)
    
    # Extract rectified camera matrix (K_rect) from projection matrix P
    K_rect = P[:, :3]  # 3x3 matrix
    
    # Convert rectified points to normalized coordinates in rectified frame
    x_norm_rect = (points_rect[:, 0] - K_rect[0, 2]) / K_rect[0, 0]
    y_norm_rect = (points_rect[:, 1] - K_rect[1, 2]) / K_rect[1, 1]
    
    # Form direction vectors in rectified camera frame (homogeneous coordinates)
    direction_rect = np.column_stack([x_norm_rect, y_norm_rect, np.ones(len(points_rect))])
    
    # Transform to original camera frame using inverse of rectification rotation
    direction_original = direction_rect @ R_rect.T
    
    # Avoid division by zero (handle points with infinite depth)
    if np.any(np.abs(direction_original[:, 2]) < 1e-8):
        # Set points at infinity to large values
        direction_original[:, 2] = np.sign(direction_original[:, 2]) * 1e8
    
    # Convert back to normalized coordinates in original frame
    x_norm_original = direction_original[:, 0] / direction_original[:, 2]
    y_norm_original = direction_original[:, 1] / direction_original[:, 2]
    
    # Project normalized coordinates to unrectified image using original camera
    points_3d = np.column_stack([x_norm_original, y_norm_original, np.ones(len(x_norm_original))])
    points_3d = points_3d.reshape(-1, 1, 3)  # Required format for projectPoints
    
    unrectified_points, _ = cv.projectPoints(
        points_3d,
        rvec=np.zeros(3),  # No rotation (camera coordinates)
        tvec=np.zeros(3),  # No translation (camera coordinates)
        cameraMatrix=K,
        distCoeffs=D
    )
    
    return unrectified_points.reshape(-1, 2)



def get_min_values_array(inArray):
    """
    Get the smallest valid (non-NaN) value by scanning the depth_map vertically
    within the specified horizontal range.
    
    Parameters:
    depth_map (numpy.ndarray): 2D array containing valid values and NaN values
    inHoriRangeStart (int): Starting column index (inclusive)
    inHoriRangeEnd (int): Ending column index (exclusive)
    
    Returns:
    float: The smallest valid value in the specified range, or NaN if no valid values exist
    """
    # Validate input parameters
    if inArray.size == 0:
        return np.nan
    
    sub_array = inArray
    
    # Find the minimum value ignoring NaN values
    #min_value = np.nanmin(sub_array)
    # np.nanmin returns NaN if all values are NaN, which is the desired behavior
    #return min_value


    # Find the minimum value for each row, ignoring nan values
    #min_values_per_row = np.nanmin(sub_array, axis=0)
    

    # Replace nan values with a very large float (something larger than any expected value in your data)
    sub_array[np.isnan(sub_array)] = float('inf')
    # Find the minimum value for each row, ignoring the artificially introduced maximum values
    min_values_per_row = np.amin(sub_array, axis=0)
    # Identify indices where we artificially placed float('inf'); these will be replaced with -1
    inf_indices = np.where(min_values_per_row == float('inf'))
    # Replace those min values with -1
    min_values_per_row[inf_indices[0]] = -1
    
    return min_values_per_row



def process_outliers_iqr(data):
    """
    Process each column of a 2D ndarray to handle outliers using IQR method.
    
    Steps for each column:
    1) Get non-nan values
    2) Get median of the non-nan values 
    3) Get quartile and IQR values
    4) Set data values below Q1−1.5×IQR to nan
    5) Set data values above Q3+1.5×IQR to nan
    
    Parameters:
    data (np.ndarray): 2D NumPy array that may contain NaN values
    
    Returns:
    np.ndarray: Modified array with outliers set to NaN
    """
    # Create a copy to avoid modifying the original array
    result = data.copy()
    
    # Process each column
    for col_idx in range(data.shape[1]):
        column = data[:, col_idx]
        
        # 1) Get non-nan values
        non_nan_mask = ~np.isnan(column)
        non_nan_values = column[non_nan_mask]
        
        # Skip column if all values are NaN or if there are no non-NaN values
        if len(non_nan_values) == 0:
            continue
        
        '''
        # 2) Get median of non-nan values
        #median_val = np.median(non_nan_values)
        
        # 3) Get quartiles and IQR
        #q1 = np.percentile(non_nan_values, 25)
        q3 = np.percentile(non_nan_values, 75)
        iqr = q3 - q1
        
        # 4 & 5) Calculate outlier bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        '''
        
        # 2) Calculate mean and standard deviation of non-nan values
        mean_val = np.mean(non_nan_values)
        std_val = np.std(non_nan_values, ddof=0)  # Population standard deviation
        
        # Handle case where standard deviation is 0 (all values are the same)
        if std_val == 0:
            continue
        
        # 3 & 4) Calculate outlier bounds using mean ± 3 standard deviations (common approach)
        # You can adjust the multiplier (3) based on your needs (e.g., 2 for more sensitive, 4 for less sensitive)
        lower_bound = mean_val - 3 * std_val
        upper_bound = mean_val + 3 * std_val
    
        # Set outliers to NaN
        # Values below lower bound
        result[(column < lower_bound) & non_nan_mask, col_idx] = np.nan
        # Values above upper bound  
        result[(column > upper_bound) & non_nan_mask, col_idx] = np.nan
    
    return result



def get_depth_of_rectified_rect(data, rectangle):
    """
    Extract and analyze a rectangular patch from an ndarray with NaN values.
    
    Parameters:
    -----------
    data : numpy.ndarray
        Input array that may contain NaN values
    rectangle : list or tuple
        Rectangle definition [x, y, w, h] where:
        - x, y: top-left corner coordinates
        - w: width (number of columns)
        - h: height (number of rows)
    
    Returns:
    --------
    tuple: (min_val, max_val, median_val)
        Minimum, maximum, and median values of the filtered patch
        Returns (np.nan, np.nan, np.nan) if no valid values remain after filtering
    """
    # For int values
    #x, y, w, h = rectangle
    # For np.float64 values
    x = int(rectangle[0])
    y = int(rectangle[1])
    w = int(rectangle[2])
    h = int(rectangle[3])
    
    [h_data, w_data] = data.shape
    
    # Make the patch stay inside the depth map
    x_min = max(0, min(x, w_data-1))
    y_min = max(0, min(y, h_data-1))
    x_max = max(0, min(x+w, w_data-1))
    y_max = max(0, min(y+h, h_data-1))
    
    # Extract the rectangular patch
    patch = data[y_min:y_max, x_min:x_max]
    
    #print(f'{[x, y, w, h]} - {data.shape} - {patch.shape}')
    
    # Get non-NaN values
    valid_values = patch[~np.isnan(patch)]
    
    # If no valid values, return NaNs
    if len(valid_values) == 0:
        return (np.nan, np.nan, np.nan)
    
    # Calculate quartiles and IQR
    q1 = np.nanpercentile(valid_values, 25)
    q3 = np.nanpercentile(valid_values, 75)
    iqr = q3 - q1
    
    # Calculate bounds for outlier filtering
    #lower_bound = q1 - 1.5 * iqr
    #upper_bound = q3 + 1.5 * iqr
    lower_bound = q1 - 1.0 * iqr
    upper_bound = q3 + 1.0 * iqr
    
    # Filter values within bounds (remove outliers)
    filtered_values = valid_values[(valid_values >= lower_bound) & 
                                   (valid_values <= upper_bound)]
    
    # If all values were outliers, fall back to original valid values
    if len(filtered_values) == 0:
        filtered_values = valid_values
    
    # Calculate min, max, and median
    min_val = np.min(filtered_values)
    max_val = np.max(filtered_values)
    median_val = np.median(filtered_values)
    
    return (min_val, max_val, median_val)




def find_openings(depth_float, min_safe_depth=500, min_opening_width=5, max_depth_threshold=3000):
    
    # Create a safe mask
    safe_mask = (depth_float > min_safe_depth) & (depth_float < max_depth_threshold) & (depth_float != -1)
    
    # Find consecutive safe regions
    openings = []
    current_start = None
    for i, is_safe in enumerate(safe_mask):
        if is_safe and current_start is None:
            # Start of a new safe region
            current_start = i
        elif not is_safe and current_start is not None:
            # End of a safe region
            if (i - current_start) >= min_opening_width:
                # Calculate average depth for this opening
                #opening_depths = depth_float[current_start:i]
                #avg_depth = np.mean(opening_depths)
                #openings.append((current_start, i-1, avg_depth))
                
                current_width = i - current_start
                start_idx = current_start
                end_idx = i - 1
                opening_data = depth_float[start_idx:end_idx]  
                openings.append({
                    'start_idx': int(start_idx),
                    'end_idx': int(end_idx),
                    'width': int(current_width),
                    'center_idx': int((start_idx + end_idx) // 2),
                    'avg_depth': float(np.mean(opening_data)),
                    'min_depth': float(np.min(opening_data)),
                    'max_depth': float(np.max(opening_data))
                })
            current_start = None
    
    # Handle case where safe region continues to the end
    if current_start is not None and (len(depth_float) - current_start) >= min_opening_width:
        #opening_depths = depth_float[current_start:]
        #avg_depth = np.mean(opening_depths)
        #openings.append((current_start, len(depth_map)-1, avg_depth))
    
        current_width = len(depth_float) - current_start
        start_idx = current_start
        end_idx = len(depth_float) - 1
        opening_data = depth_float[start_idx:end_idx]  
        openings.append({
            'start_idx': int(start_idx),
            'end_idx': int(end_idx),
            'width': int(current_width),
            'center_idx': int((start_idx + end_idx) // 2),
            'avg_depth': float(np.mean(opening_data)),
            'min_depth': float(np.min(opening_data)),
            'max_depth': float(np.max(opening_data))
        })
    
    return openings



def merge_close_openings(openings, depth_map, max_gap_distance=5, max_gap_depth_diff=100, gap_depth_threshold=300):
    """
    Advanced version that also checks the actual depth values in the gap between openings.
    Works with dictionary-based opening definitions.
    
    Parameters:
    - openings: list of dictionaries with keys 'start_idx', 'end_idx', 'avg_depth', etc.
    - depth_map: original depth map array to check gap values
    - max_gap_distance: maximum number of indices between openings to consider merging
    - max_gap_depth_diff: maximum difference in average depth between consecutive openings to merge
    - gap_depth_threshold: minimum depth value in the gap that still allows merging
    
    Returns:
    - list of merged openings as dictionaries with same structure as input
    """
    if not openings:
        return []
    
    if len(openings) == 1:
        return openings[:]
    
    merged_openings = []
    current_opening = openings[0].copy()  # Start with a copy of the first opening
    
    for i in range(1, len(openings)):
        prev_opening = openings[i-1]
        curr_opening = openings[i]
        
        # Check if current opening is close to previous opening
        gap_start = prev_opening['end_idx'] + 1
        gap_end = curr_opening['start_idx'] - 1
        
        gap_exists = gap_start <= gap_end
        gap_distance = gap_end - gap_start + 1 if gap_exists else 0
        
        # Check if depths are similar enough to merge
        depth_diff = abs(prev_opening['avg_depth'] - curr_opening['avg_depth'])
        
        # If there's a gap, check if it's safe to merge based on gap values
        can_merge_gap = True
        if gap_exists and gap_distance <= max_gap_distance:
            gap_values = depth_map[gap_start:gap_end+1]
            # Check if all gap values are either invalid (-1) or above threshold
            valid_gap_values = gap_values[gap_values != -1.0]
            if len(valid_gap_values) > 0:
                # If there are valid gap values, they should be above threshold
                can_merge_gap = np.all(valid_gap_values > gap_depth_threshold)
        elif gap_exists and gap_distance > max_gap_distance:
            can_merge_gap = False
        
        if (gap_distance <= max_gap_distance and 
            depth_diff <= max_gap_depth_diff and 
            can_merge_gap):
            # Merge with current opening
            # Update the current opening with merged properties
            new_start_idx = current_opening['start_idx']
            new_end_idx = curr_opening['end_idx']
            new_width = new_end_idx - new_start_idx + 1
            new_center_idx = (new_start_idx + new_end_idx) // 2
            
            # Get all valid depths from both openings and the gap
            all_valid_depths = []
            
            # Add valid depths from current (merged) opening
            current_depths = depth_map[current_opening['start_idx']:current_opening['end_idx']+1]
            all_valid_depths.extend(current_depths[current_depths != -1.0])
            
            # Add valid depths from current opening to merge
            curr_depths = depth_map[curr_opening['start_idx']:curr_opening['end_idx']+1]
            all_valid_depths.extend(curr_depths[curr_depths != -1.0])
            
            # Add valid depths from the gap (if any)
            if gap_exists:
                gap_depths = depth_map[gap_start:gap_end+1]
                all_valid_depths.extend(gap_depths[gap_depths != -1.0])
            
            if all_valid_depths:
                new_avg_depth = float(np.mean(all_valid_depths))
                new_min_depth = float(np.min(all_valid_depths))
                new_max_depth = float(np.max(all_valid_depths))
            else:
                # Fallback if no valid depths
                new_avg_depth = float((current_opening['avg_depth'] + curr_opening['avg_depth']) / 2)
                new_min_depth = min(current_opening['min_depth'], curr_opening['min_depth'])
                new_max_depth = max(current_opening['max_depth'], curr_opening['max_depth'])
            
            # Update current opening with merged properties

        
        else:
            # Add the current merged opening and start a new one
            merged_openings.append(current_opening)
            current_opening = curr_opening.copy()
    
    # Add the last opening
    merged_openings.append(current_opening)
    
    return merged_openings




def classify_openings(openings, depth_map,
                     depth_variance_threshold: float = 100.0,
                     depth_change_threshold: float = 200.0,
                     min_slope_threshold: float = 2.0):
    """
    Classify openings into different types based on depth characteristics.
    
    Parameters:
    -----------
    openings : List[Dict]
        List of opening dictionaries with start_idx, end_idx, etc.
    depth_map : np.ndarray
        Original depth map array
    depth_variance_threshold : float
        Maximum variance for "flat" openings (in mm)
    depth_change_threshold : float
        Minimum depth change for "doorway" openings (in mm)
    min_slope_threshold : float
        Minimum slope magnitude for "increasing/decreasing" classification
    
    Returns:
    --------
    List[Dict]
        Openings with added 'type' and classification metrics
    """
    
    
    classified_openings = []
    
    for opening in openings:
        start_idx = opening['start_idx']
        end_idx = opening['end_idx']
        
        # Extract depth data for this opening
        depth_data = depth_map[start_idx:end_idx]  # Assuming depth_map is a list of floats
        positions = np.arange(len(depth_data))
        
        # Calculate additional metrics for classification
        variance = np.var(depth_data)
        depth_range = opening['max_depth'] - opening['min_depth']
        
        # Calculate linear regression to detect trends
        slope, intercept, r_value, p_value, std_err = numpy_linregress(positions, depth_data)
        
        # Calculate rolling statistics for local patterns
        window_size = max(3, len(depth_data) // 5)  # Adaptive window size
        if len(depth_data) >= window_size:
            rolling_mean = np.convolve(depth_data, np.ones(window_size)/window_size, mode='valid')
            rolling_std = np.array([np.std(depth_data[i:i+window_size]) 
                                  for i in range(len(depth_data) - window_size + 1)])
            local_variance = np.mean(rolling_std)
        else:
            local_variance = variance
        
        # Classification logic
        opening_type = "unknown"
        classification_confidence = 0.0
        
        # Check for FLAT opening
        if variance < depth_variance_threshold and local_variance < depth_variance_threshold:
            opening_type = "flat"
            classification_confidence = 1.0 - (variance / depth_variance_threshold)
        
        # Check for INCREASING/DECREASING opening
        elif abs(slope) > min_slope_threshold and r_value > 0.7:
            if slope > 0:
                opening_type = "increasing"
            else:
                opening_type = "decreasing"
            classification_confidence = min(abs(slope) / (min_slope_threshold * 2), 1.0)
        
        # Check for DOORWAY opening (significant depth change)
        elif depth_range > depth_change_threshold:
            opening_type = "doorway"
            classification_confidence = min(depth_range / (depth_change_threshold * 2), 1.0)
        
        # Check for COMPLEX opening (high variance but not doorway)
        elif variance > depth_variance_threshold * 2:
            opening_type = "complex"
            classification_confidence = 0.5
        
        # Add classification results to opening
        classified_opening = opening.copy()
        classified_opening.update({
            'type': opening_type,
            'confidence': float(classification_confidence),
            'variance': float(variance),
            'depth_range': float(depth_range),
            'slope': float(slope),
            'r_squared': float(r_value ** 2),
            'local_variance': float(local_variance)
        })
        
        classified_openings.append(classified_opening)
    
    return classified_openings



def numpy_linregress(x, y):
    # Calculate slope and intercept
    slope, intercept = np.polyfit(x, y, 1)
    
    # Calculate predicted values
    y_pred = slope * np.array(x) + intercept
    
    # Calculate r_value
    r_value = np.corrcoef(x, y)[0, 1]
    
    # Calculate standard error
    n = len(x)
    residuals = np.array(y) - y_pred
    std_err = np.sqrt(np.sum(residuals**2) / (n - 2)) / np.sqrt(np.sum((np.array(x) - np.mean(x))**2))
    
    # For p_value, you would need to implement t-distribution CDF or use another library
    # Here we'll return None as a placeholder
    p_value = None
    
    return slope, intercept, r_value, p_value, std_err



#import cv2
#import numpy as np
from typing import List, Dict, Tuple

def find_one_bboxes_improved(
    obstacle_mask: np.ndarray, 
    depth_map: np.ndarray, 
    min_size: int = 200
) -> List[Dict]:
    """
    Find bounding boxes of foreground (1) regions in a binary mask.
    
    Args:
        obstacle_mask: Binary uint8 mask (0=background, 1=foreground)
        depth_map: Depth values for each pixel
        min_size: Minimum pixel area to be considered valid
    
    Returns:
        List of dictionaries with bbox, distance, area, centroid
    """
    # Ensure binary mask
    if obstacle_mask.dtype != np.uint8:
        obstacle_mask = (obstacle_mask > 0).astype(np.uint8)
    
    # Connected components (8-connectivity preserves diagonal connections)
    num_labels, labels, stats, centroids = cv.connectedComponentsWithStats(
        obstacle_mask, connectivity=8
    )
    
    bboxes = []
    for i in range(1, num_labels):  # Skip background (0)
        area = stats[i, cv.CC_STAT_AREA]
        if area < min_size:
            continue
            
        bboxes.append({
            'bbox': (
                stats[i, cv.CC_STAT_LEFT],
                stats[i, cv.CC_STAT_TOP],
                stats[i, cv.CC_STAT_WIDTH],
                stats[i, cv.CC_STAT_HEIGHT]
            ),
            'distance': np.nanmedian(depth_map[labels == i]), # Due to morphological operators, patch contains nan values
            'area': area,
            'centroid': centroids[i]
        })
    
    return bboxes




def generate_ground_plane_depth_map_from_intrinsics(
    image_width: int,
    image_height: int,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    camera_height_mm: float,
    camera_pitch_deg: float = 0.0
) -> np.ndarray:
    """
    Generates a synthetic depth map for a flat ground plane using camera intrinsics.

    This function uses a pinhole camera model with provided intrinsic parameters
    to project rays from each pixel into a 3D scene and calculate their
    intersection with a ground plane.

    Args:
        image_width (int): The width of the output image in pixels.
        image_height (int): The height of the output image in pixels.
        fx (float): Focal length in pixels along the x-axis.
        fy (float): Focal length in pixels along the y-axis.
        cx (float): Principal point x-coordinate in pixels.
        cy (float): Principal point y-coordinate in pixels.
        camera_height_mm (float): The height of the camera above the ground plane.
        camera_pitch_deg (float, optional): The pitch angle of the camera in degrees.
                                            Positive is pitching downwards.
                                            Defaults to 0.0 (perfectly horizontal).

    Returns:
        np.ndarray: A 2D NumPy array of shape (image_height, image_width)
                    containing the depth values in millimeters. Pixels that
                    do not intersect the ground plane (e.g., sky) have a
                    value of np.nan.
    """
    # --- 1. Create a Grid of Pixel Coordinates ---
    u, v = np.meshgrid(np.arange(image_width), np.arange(image_height))

    # --- 2. Calculate Ray Directions for Each Pixel ---
    # The camera looks along the +Z axis. The ground plane is at y = camera_height_mm.
    dx = (u - cx) / fx
    dy = (v - cy) / fy
    dz = np.ones_like(u)

    # Stack into a 3D direction vector array
    direction_vectors = np.stack([dx, dy, dz], axis=-1)

    # --- 3. Apply Camera Pitch Rotation ---
    if camera_pitch_deg != 0.0:
        pitch_rad = np.deg2rad(camera_pitch_deg)
        # Rotation matrix around the X-axis
        rotation_matrix = np.array([
            [1, 0, 0],
            [0, np.cos(pitch_rad), -np.sin(pitch_rad)],
            [0, np.sin(pitch_rad), np.cos(pitch_rad)]
        ])
        # Apply rotation to all direction vectors
        direction_vectors = direction_vectors @ rotation_matrix.T
    
    # Unpack rotated components
    dx_rot = direction_vectors[:, :, 0]
    dy_rot = direction_vectors[:, :, 1]
    dz_rot = direction_vectors[:, :, 2]

    # --- 4. Calculate Intersection with Ground Plane and Depth ---
    # The ray starts at P0 = (0, 0, 0) and has direction d = (dx, dy, dz).
    # We find intersection with the ground plane y = camera_height_mm.
    # t * dy_rot = camera_height_mm  =>  t = camera_height_mm / dy_rot
    
    depth_map = np.full((image_height, image_width), np.nan)
    
    # Only calculate for rays pointing downwards (dy > 0 in our coordinate system)
    valid_rays_mask = dy_rot > 0

    # Calculate the scaling factor 't' for valid rays
    t = camera_height_mm / dy_rot[valid_rays_mask]

    # The intersection point is P(t). The depth is the distance from the origin to P(t).
    # distance = ||P(t)|| = ||t * d|| = t * ||d||
    norm_d = np.sqrt(dx_rot[valid_rays_mask]**2 + dy_rot[valid_rays_mask]**2 + dz_rot[valid_rays_mask]**2)

    # Calculate the final depth for the valid pixels
    depth_map[valid_rays_mask] = t * norm_d

    return depth_map




def get_obstacle_mask(depthMap, depth_map_horizontal, lower_bound: int = -100, upper_bound: int = 100):
    
    
    errorDepth = depthMap - depth_map_horizontal
    #lower_bound = -100
    #upper_bound = 100
    #obstacle_mask = (errorDepth < lower_bound) | (errorDepth > upper_bound)
    obstacle_mask = (errorDepth < lower_bound)
    obstacle_mask = np.array(obstacle_mask, dtype=np.uint8)

    # Clean up
    kernel = np.ones((5, 5), np.uint8)
    obstacle_mask = cv.morphologyEx(obstacle_mask, cv.MORPH_OPEN, kernel)
    obstacle_mask = cv.morphologyEx(obstacle_mask, cv.MORPH_CLOSE, kernel)

    return obstacle_mask;

#import cv2
#import numpy as np
from typing import List, Dict, Tuple

def find_one_bboxes_improved(
    obstacle_mask: np.ndarray, 
    depth_map: np.ndarray, 
    min_size: int = 200
) -> List[Dict]:
    """
    Find bounding boxes of foreground (1) regions in a binary mask.
    
    Args:
        obstacle_mask: Binary uint8 mask (0=background, 1=foreground)
        depth_map: Depth values for each pixel
        min_size: Minimum pixel area to be considered valid
    
    Returns:
        List of dictionaries with bbox, distance, area, centroid
    """
    # Ensure binary mask
    if obstacle_mask.dtype != np.uint8:
        obstacle_mask = (obstacle_mask > 0).astype(np.uint8)
    
    # Connected components (8-connectivity preserves diagonal connections)
    num_labels, labels, stats, centroids = cv.connectedComponentsWithStats(
        obstacle_mask, connectivity=8
    )
    
    bboxes = []
    for i in range(1, num_labels):  # Skip background (0)
        area = stats[i, cv.CC_STAT_AREA]
        if area < min_size:
            continue
            
        bboxes.append({
            'bbox': (
                stats[i, cv.CC_STAT_LEFT],
                stats[i, cv.CC_STAT_TOP],
                stats[i, cv.CC_STAT_WIDTH],
                stats[i, cv.CC_STAT_HEIGHT]
            ),
            'distance': np.nanmedian(depth_map[labels == i]), # Due to morphological operators, patch contains nan values
            'area': area,
            'centroid': centroids[i]
        })
    
    return bboxes



def get_largest_space_between_rects(widthStart, widthEnd, rectangles_sorted):
    # Variables to track the largest horizontal distance and its start and end points
    largest_distance = 0
    start_rect = None
    end_rect = None
    start_point = None
    end_point = None

    x1, _, w1, _ = rectangles_sorted[0]['bbox']
    x2, _, w2, _ = rectangles_sorted[-1]['bbox']
    if x1-widthStart > widthEnd -(x2+w2):
        largest_distance = np.int32(x1-widthStart)
        start_point = np.int32(widthStart)
        end_point = np.int32(x1)
    else :
        largest_distance = np.int32(widthEnd -(x2+w2))
        start_point = np.int32(x2+w2)
        end_point = np.int32(widthEnd)


    # Iterate over consecutive pairs of rectangles to find the largest horizontal distance
    for i in range(len(rectangles_sorted) - 1):
        rect1 = rectangles_sorted[i]
        rect2 = rectangles_sorted[i + 1]
        
        # Get the right edge of the first rectangle and the left edge of the second
        x1, _, w1, _ = rect1['bbox']
        x2, _, _, _ = rect2['bbox']
        
        right_edge_1 = x1 + w1  # Right edge of the first rectangle
        left_edge_2 = x2        # Left edge of the second rectangle
        
        # Calculate the horizontal distance between consecutive rectangles
        distance = left_edge_2 - right_edge_1
        
        # If this is the largest distance, update the variables
        if distance > largest_distance:
            largest_distance = distance
            #start_rect = rect1
            #end_rect = rect2
            start_point = right_edge_1
            end_point = left_edge_2
    
    return  {
                'dist': largest_distance.item(), # Largest Horizontal Distance
                #'left_rect': start_rect,   # Start Rectangle (left to right)
                #'right_rect': end_rect,    # End Rectangle
                'left_start': start_point.item(), # Start Point (Right Edge of Start Rectangle)
                'right_end': end_point.item()     # End Point (Left Edge of End Rectangle)
            }

def get_move_direction(P1, num_disp, imWidth, obstacle_list):
    pp_cx = P1[0, 2]  # principal point x
    #pp_cy = P1[1, 2]   # principal point y
    hfov_half = 81.20/imWidth
    #vfov_half = 69.71/imHeight

    sorted_obstacle = sorted(obstacle_list, key=lambda rect: rect['bbox'][0])
    sorted_obstacle = list(filter(lambda rect: rect['distance'] < 1000, sorted_obstacle))
    
    
    #print(sorted_obstacle)
                    
    '''
    for rect in sorted_obstacle:
        centro_x, centro_y = rect['centroid'];
        centroAng_x = (centro_x-pp_cx)*hfov_half
        centroAng_y = (centro_y-pp_cy)*vfov_half
        depth = rect['distance']
        print(f"x: {centroAng_x:.2f}, y: {centroAng_y:.2f}, depth: {depth:.2f}")
    '''

    empty_space = None
    if len(sorted_obstacle) == 0:
        return None
    
    if len(sorted_obstacle) > 1:
        # Find empty space between regions
        empty_space = get_largest_space_between_rects(num_disp, imWidth, sorted_obstacle)
        print(empty_space)
    else:
        # Find the distance between edges
        x1, _, w1, _ = obstacle_list[0]['bbox']
        leftDist = x1-num_disp # stere depth extractions "num_disp" parameter defines the left edge
        rightDist =  imWidth - (x1+w1)
        if (leftDist > rightDist):
            empty_space ={'dist': leftDist, # Largest Horizontal Distance
                    'left_start': num_disp,
                    'right_end': x1
                    }
        else :
            empty_space ={'dist': rightDist, # Largest Horizontal Distance
                    'left_start': x1+w1,
                    'right_end': imWidth
                    }

    if empty_space is not None:
        centerAngle = ((empty_space['left_start']+empty_space['right_end'])/2-pp_cx)*hfov_half
        print(f'Turn degrees: {centerAngle:.2f}')
        return {'dist': empty_space['dist'], # Largest Horizontal Distance
                'left_start': empty_space['left_start'],
                'right_end': empty_space['right_end'],
                'angle':centerAngle}
    return None