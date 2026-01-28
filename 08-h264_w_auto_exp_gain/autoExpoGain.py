
"""
Auto Exposure and Gain Control Class
"""

import threading
import time
import numpy as np  # Added missing import

# Import camera control interface
from qCU_CCtrl import qCU_CCtrl


class AutoExposureGain:
    def __init__(self, cctrl_ranges, target_brightness=128, tolerance=10, adjustment_factor=0.5):
        """
        Initialize auto exposure/gain controller.
        
        Args:
            target_brightness (int): Target mean brightness (0-255)
            tolerance (int): Acceptable deviation from target
            adjustment_factor (float): Damping factor for adjustments (0.0-1.0)
        """
        self.target_brightness = target_brightness
        self.tolerance = tolerance
        self.adjustment_factor = adjustment_factor
        
        # Camera control ranges (set during start)
        if len(cctrl_ranges) != 4:
            raise ValueError("cctrl_ranges must contain exactly 4 values: [expo_min, expo_max, gain_min, gain_max]")
        
        self._expo_min, self._expo_max, self._gain_min, self._gain_max = cctrl_ranges
        
        # Threading state
        self._timer = None
        self._running = False
        self._interval_sec = None
        
        # Callback functions
        self._auto_func = None
        self._data_func = None
        
    def _default_auto_func(self, in_data):
        """Default automatic adjustment function."""
        frame = in_data  # Assuming in_data is the frame
        
        # Compute mean brightness (works for grayscale or color frames)
        current_mean = np.mean(frame)
        
        #print(f"curMean: {current_mean:.2f}")
        
        # Check if already within tolerance
        if abs(current_mean - self.target_brightness) < self.tolerance:
            return
        
        # Initialize the camera control innterface
        cameraCtrl = qCU_CCtrl()
        
        # Get current exposure and gain (assuming cameraCtrl is accessible)
        # Note: You'll need to ensure cameraCtrl is available in scope
        expo, gain, _ = cameraCtrl.get_expo_gain()
        
        # Calculate proportional factor to reach target (avoid division by zero)
        factor = self.target_brightness / max(current_mean, 1e-6)
        
        # Dampen the factor for smoother adjustments
        damped_factor = 1 + self.adjustment_factor * (factor - 1)
        
        new_expo = expo;
        new_gain = gain;
        # Check whether we are going to increase or decrease the brigthness
        if (factor > 1):
            # Increase brigthness with exposure first schemenew_expo = int(expo * damped_factor)
            new_expo = int(expo * damped_factor)
            new_expo = max(self._expo_min, min(new_expo, self._expo_max))
            if new_expo != expo:
                cameraCtrl.set_expo_gain(new_expo, gain)
                
            else:
                # If exposure can't be adjusted further, adjust gain
                new_gain = int(gain * damped_factor)
                new_gain = max(self._gain_min, min(new_gain, self._gain_max))
                
                if new_gain != gain:
                    cameraCtrl.set_expo_gain(new_expo, new_gain)
        
        else :
            # Decrease brigthness with gain first scheme
            new_gain = int(gain * damped_factor)
            new_gain = max(self._gain_min, min(new_gain, self._gain_max))
            
            if new_gain != gain:
                cameraCtrl.set_expo_gain(expo, new_gain)           
            else:
                # If gain can't be adjusted further, adjust exposure
                new_expo = int(expo * damped_factor)
                new_expo = max(self._expo_min, min(new_expo, self._expo_max))
                
                if new_expo != expo:
                    cameraCtrl.set_expo_gain(new_expo, gain)
        
        if new_expo != expo or new_gain != gain:
            print(f"curMean: {current_mean:.2f} | {expo} -> {new_expo} / {gain} -> {new_gain}")
        
        # Remove camera control interface
        del cameraCtrl
        
    
    def start(self, auto_func=None, data_func=None, interval_ms=1000):
        """
        Start the automatic exposure/gain control thread.
        
        Args:
            cctrl_ranges (list): [expo_min, expo_max, gain_min, gain_max]
            auto_func (callable): Function to call for adjustments (optional)
            data_func (callable): Function to get input data (required if auto_func provided)
            interval_ms (int): Adjustment interval in milliseconds
        """

        if self._running == True:
            print(f"Auto Exposure Gain is already running")
        
        
        if auto_func is not None:
            if data_func is None:
                raise ValueError("data_func must be provided when auto_func is specified")
            self._auto_func = auto_func
            self._data_func = data_func
        else:
            # Use default implementation
            self._auto_func = self._default_auto_func
            if data_func is None:
                raise ValueError("data_func must be provided for default auto function")
            self._data_func = data_func
        
        if not self._running:
            self._interval_sec = interval_ms / 1000.0
            self._running = True
            self._schedule_next_run()
    
    def _schedule_next_run(self):
        """Schedule the next execution of the auto function."""
        if not self._running:
            return
            
        #try:
        data = self._data_func()  # Get the data for processing
        #print(data)
        #self._auto_func(data)
        
        if data is not None:
            self._auto_func(data)     # Apply adjustments
        else:
            print(f"   AutoExpGain: No image data!!!")
        
        #except Exception as e:
         #   print(f"Error in auto exposure/gain function: {e}")
            # Depending on your needs, you might want to stop here or continue
        
        # Reschedule the next execution
        if self._running:
            self._timer = threading.Timer(self._interval_sec, self._schedule_next_run)
            self._timer.start()
    
    def stop(self):
        """Stop the automatic exposure/gain control thread."""
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        print("Auto exposure/gain control stopped.")
    
    @property
    def is_running(self):
        """Check if the auto control is currently running."""
        return self._running


# Example usage:
# auto_eg = AutoExposureGain(target_brightness=128, tolerance=10, adjustment_factor=0.5)
# auto_eg.start(
#     cctrl_ranges=[100, 10000, 0, 24], 
#     data_func=lambda: get_current_frame(),  # Your frame acquisition function
#     interval_ms=200
# )
# 
# Later...
# auto_eg.stop()




'''
import threading
import time

# Global variables to keep track of the timer and state
timer = None
running = False
interval_sec = None

_expo_min = None
_expo_max = None
_gain_min = None
_gain_max = None
#
target_brightness=128, tolerance=10, adjustment_factor=0.5


def defualt_auto_func(inData):

    # Compute mean brightness (works for grayscale or color frames)
    current_mean = np.mean(frame)
    
    # Check if already within tolerance
    if abs(current_mean - target_brightness) < tolerance:
        return
    
    # Get current exposure and gain
    expo, gain, _ = cameraCtrl.get_expo_gain()
    
    # Calculate proportional factor to reach target (avoid division by zero)
    factor = target_brightness / max(current_mean, 1e-6)
    
    # Dampen the factor for smoother adjustments
    damped_factor = 1 + adjustment_factor * (factor - 1)
    
    # Try adjusting exposure first
    new_expo = int(expo * damped_factor)
    new_expo = max(CAM_EXPOSURE_MIN, min(new_expo, CAM_EXPOSURE_MAX))
    
    if new_expo != expo:
        cameraCtrl.set_expo_gain(new_expo, gain)
        return  # Exit after adjusting exposure
    
    # If exposure can't be adjusted further, adjust gain
    new_gain = int(gain * damped_factor)
    new_gain = max(CAM_GAIN_MIN, min(new_gain, CAM_GAIN_MAX))
    
    if new_gain != gain:
        cameraCtrl.set_expo_gain(expo, new_gain)
        
    return;


def start_autoEG_thread(cctrlRanges, auto_func, data_func, interval_ms):
    """Start the periodic task with the specified function"""
    global timer, running, interval_sec
    
    if(len(cctrlRanges) != 4):
        raise RuntimeError("invalid camera control range.")
    
    global _expo_min = cctrlRanges[0]
    global _expo_max = cctrlRanges[1]
    global _gain_min = cctrlRanges[2]
    global _gain_max = cctrlRanges[3]

    
    if not running:
        interval_sec = interval_ms / 1000.0  # Convert milliseconds to seconds
        running = True
        _schedule_next_run(auto_func, data_func)

def _schedule_next_run(my_function):
    """Schedule the next execution of the function"""
    global timer
    if running:
        data = data_func()  # Get the data for the function to process
        auto_func(data)  # Call the passed function with the data
        # Reschedule the next execution
        timer = threading.Timer(interval_sec, _schedule_next_run, [auto_func, data_func])
        timer.start()

def stop_autoEG_thread():
    """Stop the periodic task"""
    global timer, running
    if running:
        running = False
        if timer is not None:
            timer.cancel()  # Cancel the timer if it's running
        print("Function stopped.")
'''