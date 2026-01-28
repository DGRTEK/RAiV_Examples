import cv2 as cv
import numpy as np

from qCU_Data import qCUData

import depthUtils


class StereoDepthEstimator:
    def __init__(
        self,
        scale_factor: float = 0.5,
        min_depth: float = 100.0,
        max_depth: float = 550.0,
        sgbm_params: dict = None
    ):
        
        self.scale_factor = scale_factor
        self.min_depth = min_depth
        self.max_depth = max_depth

        # Get calibration and rectification paramters
        [self.K1, self.D1, self.K2, self.D2, self.R, self.T] = qCUData.load_calibration()
        [self.R1, self.R2, self.P1, self.P2, self.Q, self.roi1, self.roi2] = qCUData.load_rectification()

        '''
        default_sgbm = {
            'blockSize': 3,
            'minDisparity': 0,
            'numDisparities': 160,
            'uniquenessRatio': 5,
            'speckleWindowSize': 3,
            'speckleRange': 3,
            'disp12MaxDiff': -1,
            'P1': 6,
            'P2': 24,
            #'mode': cv.STEREO_SGBM_MODE_SGBM
            'mode': cv.STEREO_SGBM_MODE_SGBM_3WAY
        }
        '''
        '''
        default_sgbm = {
            'blockSize': 9,
            'minDisparity': 50,
            'numDisparities': 160,
            'uniquenessRatio': 15,
            'speckleWindowSize': 3,
            'speckleRange': 3,
            'disp12MaxDiff': 1,
            'P1': 6,
            'P2': 24,
            #'mode': cv.STEREO_SGBM_MODE_SGBM
            #'mode': cv.STEREO_SGBM_MODE_HH4
            'mode': cv.STEREO_SGBM_MODE_SGBM_3WAY
        }
        '''
        
        # Video version
        default_sgbm = {
            'blockSize': 5,
            'minDisparity': 50,
            'numDisparities': 160,
            'uniquenessRatio': 5,
            'speckleWindowSize': 3,
            'speckleRange': 3,
            'disp12MaxDiff': -1,
            'P1': 6,
            'P2': 24,
            #'mode': cv.STEREO_SGBM_MODE_SGBM
            'mode': cv.STEREO_SGBM_MODE_SGBM_3WAY
        }
        
        
        
        '''
        default_sgbm = {
            'minDisparity': 0,
            'numDisparities':  96,        # Must be a multiple of 16
            'blockSize': 3,              # A more common, balanced size
            'P1': 8 *3*3, #8 * 3 * 3,             # Formula: 8 * blockSize^2
            'P2': 32 *3*3, #32 * 3 * 3,            # Formula: 32 * blockSize^2
            'disp12MaxDiff': 1,          # Enable consistency check
            'uniquenessRatio': 5,
            'speckleWindowSize': 9, #100,
            'speckleRange': 9, #32,
            'preFilterCap': 63,          # (Not in your list, but good to have)
            #'mode': cv.STEREO_SGBM_MODE_SGBM #cv.STEREO_SGBM_MODE_HH
            'mode': cv.STEREO_SGBM_MODE_SGBM_3WAY
        }
        '''
        
        if sgbm_params:
            default_sgbm.update(sgbm_params)
        self.sgbm_params = default_sgbm
        
        self.stereo_sgbm = cv.StereoSGBM_create(**self.sgbm_params)
        
        # Initialize rectification maps as None
        self.mapL1 = self.mapL2 = self.mapR1 = self.mapR2 = None
        self.rectification_initialized = False



    def _initialize_rectification_maps(self, img_height: int, img_width: int):
        """Initialize rectification maps once based on image dimensions"""
        if self.rectification_initialized:
            return
            
        h, w = int(img_height * self.scale_factor), int(img_width * self.scale_factor)
        self.mapL1, self.mapL2 = cv.initUndistortRectifyMap(
            self.K1, self.D1, self.R1, self.P1, (w, h), cv.CV_32F
        )
        self.mapR1, self.mapR2 = cv.initUndistortRectifyMap(
            self.K2, self.D2, self.R2, self.P2, (w, h), cv.CV_32F
        )
        self.rectification_initialized = True

    '''
    def preprocess_images(self, imgL_rgb: np.ndarray, imgR_rgb: np.ndarray) -> tuple:
        """
        Accepts (H, W, 3) RGB arrays.
        Converts to BGR → resizes → extracts Y (luminance).
        """
        # Convert RGB → BGR for OpenCV
        imgL_bgr = cv.cvtColor(imgL_rgb, cv.COLOR_RGB2BGR)
        imgR_bgr = cv.cvtColor(imgR_rgb, cv.COLOR_RGB2BGR)

        # Resize
        #new_w = int(self.orig_w * self.scale_factor)
        #new_h = int(self.orig_h * self.scale_factor)
        new_width = int(imgL_rgb.shape[1] * self.scale_factor)
        new_height = int(imgL_rgb.shape[0] * self.scale_factor)
        #imgL_bgr = cv.resize(imgL_bgr, (new_width, new_height))
        #imgR_bgr = cv.resize(imgR_bgr, (new_width, new_height))
        if self.scale_factor < 1.0:
            imgL_bgr = cv.resize(imgL_bgr, (new_width, new_height), interpolation=cv.INTER_AREA)
            imgR_bgr = cv.resize(imgR_bgr, (new_width, new_height), interpolation=cv.INTER_AREA)
        else:
            imgL_bgr = cv.resize(imgL_bgr, (new_width, new_height), interpolation=cv.INTER_LINEAR)
            imgR_bgr = cv.resize(imgR_bgr, (new_width, new_height), interpolation=cv.INTER_LINEAR)

        # Extract Y channel
        imgL_y = cv.cvtColor(imgL_bgr, cv.COLOR_BGR2YUV)[:, :, 0]
        imgR_y = cv.cvtColor(imgR_bgr, cv.COLOR_BGR2YUV)[:, :, 0]

        return imgL_y, imgR_y
    '''
    def preprocess_images(self, imgL_rgb: np.ndarray, imgR_rgb: np.ndarray) -> tuple:
            """
            Accepts (H, W, 3) RGB arrays.
            Converts to BGR → resizes → extracts Y (luminance).
            """
            # Convert RGB → BGR for OpenCV
            imgL_Y_ori = cv.cvtColor(imgL_rgb, cv.COLOR_RGB2YUV)[:, :, 0]
            imgR_Y_ori = cv.cvtColor(imgR_rgb, cv.COLOR_RGB2YUV)[:, :, 0]
            
            # Resize
            new_width = int(imgL_Y_ori.shape[1] * self.scale_factor)
            new_height = int(imgL_Y_ori.shape[0] * self.scale_factor)
            #imgL_bgr = cv.resize(imgL_bgr, (new_width, new_height))
            #imgR_bgr = cv.resize(imgR_bgr, (new_width, new_height))
            if self.scale_factor < 1.0:
                imgL_y = cv.resize(imgL_Y_ori, (new_width, new_height), interpolation=cv.INTER_AREA)
                imgR_y = cv.resize(imgR_Y_ori, (new_width, new_height), interpolation=cv.INTER_AREA)
            else:
                imgL_y = cv.resize(imgL_Y_ori, (new_width, new_height), interpolation=cv.INTER_LINEAR)
                imgR_y = cv.resize(imgR_Y_ori, (new_width, new_height), interpolation=cv.INTER_LINEAR)
            
            return imgL_y, imgR_y


    def rectify_images(self, imgL: np.ndarray, imgR: np.ndarray) -> tuple:
        #h, w = imgL.shape[:2]
        #mapL1, mapL2 = cv.initUndistortRectifyMap(self.K1, self.D1, self.R1, self.P1, (w, h), cv.CV_32F)
        #mapR1, mapR2 = cv.initUndistortRectifyMap(self.K2, self.D2, self.R2, self.P2, (w, h), cv.CV_32F)

        #imgL_rect = cv.remap(imgL, mapL1, mapL2, cv.INTER_LINEAR)
        #imgR_rect = cv.remap(imgR, mapR1, mapR2, cv.INTER_LINEAR)
        
        imgL_rect = cv.remap(imgL, self.mapL1, self.mapL2, cv.INTER_LINEAR)
        imgR_rect = cv.remap(imgR, self.mapR1, self.mapR2, cv.INTER_LINEAR)

        x, y, w_roi, h_roi = self.roi1
        imgL_rect = imgL_rect[y:y+h_roi, x:x+w_roi]
        imgR_rect = imgR_rect[y:y+h_roi, x:x+w_roi]

        self.Q_updated = self.Q.copy()
        self.Q_updated[0, 3] -= x
        self.Q_updated[1, 3] -= y

        return imgL_rect, imgR_rect

    '''
    def compute_disparity(self, imgL_rect: np.ndarray, imgR_rect: np.ndarray) -> np.ndarray:
        disp = self.stereo_sgbm.compute(imgL_rect, imgR_rect).astype(np.float32) / 16.0
        disp[disp <= 0] = np.nan
        return disp
    '''
    # Consider using OpenCL acceleration if available
    def compute_disparity(self, imgL_rect: np.ndarray, imgR_rect: np.ndarray) -> np.ndarray:
        # Use UMat for GPU acceleration if available
        if hasattr(cv, 'UMat'):
            imgL_rect = cv.UMat(imgL_rect)
            imgR_rect = cv.UMat(imgR_rect)
        
        disp = self.stereo_sgbm.compute(imgL_rect, imgR_rect)
        
        if hasattr(cv, 'UMat'):
            disp = disp.get()  # Convert back to numpy array
        
        disp = disp.astype(np.float32) / 16.0
        disp[disp <= 0] = np.nan
        return disp

    def compute_depth_map(self, disparity: np.ndarray) -> np.ndarray:
        points_3D = cv.reprojectImageTo3D(disparity, self.Q_updated)
        depth = points_3D[:, :, 2]
        depth[depth <= 0] = np.nan
        depth[depth > self.max_depth] = np.nan
        depth[depth < self.min_depth] = np.nan
        return depth

    def depth_to_colormap(self, depth_map: np.ndarray, colormap=cv.COLORMAP_VIRIDIS, nan_color=[0, 0, 0]) -> np.ndarray:
        nan_mask = np.isnan(depth_map)
        depth_filled = np.nan_to_num(depth_map, nan=self.min_depth)
        depth_clipped = np.clip(depth_filled, self.min_depth, self.max_depth)

        depth_range = self.max_depth - self.min_depth
        if depth_range > 0:
            normalized = ((depth_clipped - self.min_depth) / depth_range * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(depth_clipped, dtype=np.uint8)

        colored = cv.applyColorMap(normalized, colormap)
        colored[nan_mask] = nan_color  # BGR
        return colored

    def process_pair_from_raster(self, imgL_rgb: np.ndarray, imgR_rgb: np.ndarray, output_path: str = None) -> np.ndarray:
        """
        Process raw raster-scanned RGB data of shape (H*W*3, 1) or (H*W*3,).

        Parameters:
        - left_raster, right_raster: 1D arrays of size H*W*3 (RGB raster order)
        - output_path: optional path to save colored depth map

        Returns:
        - depth_map: (H_rect, W_rect) float32 array with depth (NaN for invalid)
        """
        
        
        # Initialize rectification maps on first call
        if not self.rectification_initialized:
            self._initialize_rectification_maps(imgL_rgb.shape[0], imgL_rgb.shape[1])
            
        # Preprocess → rectify → compute depth
        imgL_y, imgR_y = self.preprocess_images(imgL_rgb, imgR_rgb)            
        imgL_rect, imgR_rect = self.rectify_images(imgL_y, imgR_y)
        disp = self.compute_disparity(imgL_rect, imgR_rect)
        depth_map = self.compute_depth_map(disp)
        '''
        if output_path:
            colored = self.depth_to_colormap(depth_map)
            cv.imwrite(output_path, colored)
            print(f"Saved depth map to: {output_path}")
        '''
        return depth_map
    
    def get_depth_of_rect(self, data, unrect_rectangle):
        x_im = unrect_rectangle[0]*self.scale_factor
        y_im = unrect_rectangle[1]*self.scale_factor
        w_im = unrect_rectangle[2]*self.scale_factor
        h_im = unrect_rectangle[3]*self.scale_factor
        unrectified_coords = np.array([[x_im, y_im], [x_im+w_im, y_im+h_im]], dtype=np.float32)
        rectified_coords_left = depthUtils.unrectified_to_rectified_coords_pmatrix(unrectified_coords, self.K1, self.D1, self.P1)
        x_3d, y_3d = rectified_coords_left[0, 0]-self.roi1[0], rectified_coords_left[0, 1]-self.roi1[1]
        w_3d, h_3d = rectified_coords_left[1, 0]-rectified_coords_left[0, 0], rectified_coords_left[1, 1]-rectified_coords_left[0, 1]
        rectangle = [x_3d, y_3d, w_3d, h_3d]
        
        depth_min_val, depth_max_val, depth_median_val = depthUtils.get_depth_of_rectified_rect(data, rectangle)

        return (depth_min_val, depth_max_val, depth_median_val)
