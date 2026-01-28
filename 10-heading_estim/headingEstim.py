import time
from qCU_Data import qCUData
import threading

import collections
from typing import Any, Optional, List


def estimate_IMU_bias(theQCUData, maxCount):
    """
    Estimates the gyro bias by averaging readings while the IMU is stationary.

    Args:
        theQCUData: An object with a getDataRawImu() method that returns 
                    (raw_imu_data_dict, current_imu_index).
        maxCount (int): The number of samples to collect for the average.

    Returns:
        dict: A dictionary containing the estimated bias for each gyro axis.
              e.g., {'bias_x': value, 'bias_y': value, 'bias_z': value}
    """
    print("\nCalibration started.")
    # --- Initialization ---
    gyro_x_sum = 0.0
    gyro_y_sum = 0.0
    gyro_z_sum = 0.0
    #
    accel_x_sum = 0.0
    accel_y_sum = 0.0
    accel_z_sum = 0.0
    
    # This timing logic is kept from your original function
    target_interval = 1.0 / (200.0*2) # *2 for nyquist rate
    last_index = None
    
    count = 0
    
    start = time.time()
    while count < maxCount:
        #start = time.time()
        
        raw_imu_data, current_imu_index = theQCUData.getDataRawImu()
        
        # Process data only when the index changes (new data available)
        if last_index is not None and current_imu_index != last_index:
            
            #print(f"  accel: {raw_imu_data['accel_x']:.3f} - {raw_imu_data['accel_y']:.3f} - {raw_imu_data['accel_z']:.3f}")
            
            # Accumulate the gyro readings
            gyro_x_sum += raw_imu_data['gyro_x']
            gyro_y_sum += raw_imu_data['gyro_y']
            gyro_z_sum += raw_imu_data['gyro_z']
            
            accel_x_sum += raw_imu_data['accel_x']
            accel_y_sum += raw_imu_data['accel_y']
            accel_z_sum += raw_imu_data['accel_z']
            
            count += 1
            #print(f"Collecting sample {count}/{maxCount}")
            
        last_index = current_imu_index
        
        '''
        # Maintain 100Hz (as per original logic)
        elapsed = time.time() - start
        sleep_time = target_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        '''
    elapsed = time.time() - start
    # --- Calculate and return the bias ---
    print(f"\nCalibration complete. {elapsed:.3f}")
    
    # Avoid division by zero if no samples were collected
    if count == 0:
        print("Error: No data was collected. Cannot estimate bias.")
        return {'bias_x': 0.0, 'bias_y': 0.0, 'bias_z': 0.0}

    gyro_bias_x = gyro_x_sum / count
    gyro_bias_y = gyro_y_sum / count
    gyro_bias_z = gyro_z_sum / count
    #
    accel_bias_x = accel_x_sum / count
    accel_bias_y = accel_y_sum / count
    accel_bias_z = accel_z_sum / count

    
    print(f"  accel_bias: {accel_bias_x:.3f} - {accel_bias_y:.3f} - {accel_bias_z:.3f}")
    print(f"  gyro_bias: {gyro_bias_x:.3f} - {gyro_bias_y:.3f} - {gyro_bias_z:.3f}")
    
     
    return {'accel_bias_x': accel_bias_x, 'accel_bias_y': accel_bias_y, 'accel_bias_z': accel_bias_z}, {'gyro_bias_x': gyro_bias_x, 'gyro_bias_y': gyro_bias_y, 'gyro_bias_z': gyro_bias_z}




class HeadingEstimator(threading.Thread):
    def __init__(self, theQCUData, gyro_bias, update_rate_hz=200, buffer_size: int = 200):
        super().__init__()
        self.theQCUData = theQCUData
        self.gyro_bias = gyro_bias
        self.update_rate_hz = update_rate_hz

        self._heading_deg = 0.0
        self._heading_lock = threading.Lock()
        self._stop_event = threading.Event()

        # Target loop interval (Nyquist-adjusted as in your original)
        self._target_interval = 1.0 / (update_rate_hz * 2)

        # Ring buffer to hold a collection of heading estimates
        self._buffer = collections.deque(maxlen=buffer_size)
        self._buffer_lock = threading.RLock()  # Thread-safe access to buffer

    def run(self):
        last_index = None
        last_time = time.time()

        try:
            while not self._stop_event.is_set():
                #start = time.time()

                raw_imu_data, current_imu_index = self.theQCUData.getDataRawImu()
                #print(f"  {current_imu_index} - {raw_imu_data}")

                curImuTs = raw_imu_data['timestamp'];
                
                if last_index is not None and current_imu_index != last_index:
                    # Use fixed dt = 0.005 (i.e., 200 Hz)
                    dt = 0.005

                    #print(f"{raw_imu_data['timestamp']}")
                    
                    # ::: NOTE ::: Due to the mounting of the IMU, "gyro-z" was mirrored
                    gyro_z_corrected = -1*(raw_imu_data['gyro_z'] - self.gyro_bias['gyro_bias_z'])
                    delta_heading = gyro_z_corrected * dt

                    with self._heading_lock:
                        self._heading_deg += delta_heading
                        self._heading_deg %= 360  # Keep in [0, 360)

                    # Optional: print for debugging
                    # print(f"Heading: {self._heading_deg:.2f}°")
                    
                    
                    # Decimate and store the heading estimates
                    if (current_imu_index %20 == 0):
                        try:
                            with self._buffer_lock:
                                self._buffer.append((curImuTs, self._heading_deg))
                        except Exception as e:
                            # Handle data acquisition errors appropriately
                            print(f"Error: Heading rb  {e}")
                last_index = current_imu_index

                '''
                # Maintain loop rate
                elapsed = time.time() - start
                sleep_time = self._target_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                '''

        except Exception as e:
            print(f"Error in heading estimator thread: {e}")
        finally:
            print("Heading estimator thread stopped.")

    def get_heading(self):
        """Safely return the current heading in degrees [0, 360)."""
        with self._heading_lock:
            return self._heading_deg

    def get_heading_list(self) -> List[Any]:
        """Get all data currently in the buffer (oldest to newest)."""
        with self._buffer_lock:
            return list(self._buffer)

    def stop(self):
        """Request the thread to stop."""
        self._stop_event.set()

    def stopped(self):
        """Check if the thread has stopped."""
        return not self.is_alive()
