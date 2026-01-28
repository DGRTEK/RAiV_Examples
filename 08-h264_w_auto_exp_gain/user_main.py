import qCU_Net
import qCU_Stream
from qCU_CCtrl import qCU_CCtrl
#
from qCU_Data import qCUData
from  autoExpoGain import AutoExposureGain
#
import cv2

def get_latest_frame():

    if gQCUData is None:
        raise RuntimeError("Data interface was not initialized")

    # Get current frame
    frame = gQCUData.getDataFrame()

    if frame is None:
        return None

    #print(f"New frame received: shape {frame.shape}")

    # Process the right image
    # Convert from RGB to Grayscale
    # OpenCV assumes the data is in BGR format by default, so we need to convert it properly.
    gray_frame = cv2.cvtColor(frame[1], cv2.COLOR_RGB2GRAY)


    [monoWidth, monoHeight] = gray_frame.shape
    #print(f"Gray: shape {monoHeight}x{monoWidth}")

    # Resize the grayscale image to FRAME_WIDTH and FRAME_HEIGHT//2
    resized_gray_frame = cv2.resize(gray_frame, (monoWidth, monoHeight//2))

    #print(f"Resized: shape {resized_gray_frame.shape}")

    return resized_gray_frame



def enc_json_handler(client_socket, json_payload, client_address):
    """Custom handler that receives parsed JSON and client address."""
    print(f"Custom handler called for client {client_address}")
    print(f"Received payload: {json_payload}")

    # Check live streaming request
    if isinstance(json_payload, dict):
        if 'live_isStart' in json_payload and 'live_isStereo' in json_payload:
            isStart = json_payload['live_isStart']
            isStereo = json_payload['live_isStereo']
            print(f"Live setting start: {isStart} stereo: {isStereo}")
            qCU_Stream.setEncoderStatus(isStart, isStereo)

    # Check camera control parameter request
    if isinstance(json_payload, dict):
        if 'get_camCtrl' in json_payload:

            # Initialize the camera control object
            cameraCtrl = qCU_CCtrl()

            # Get camera control parameters
            expo, gain, ret_code = cameraCtrl.get_expo_gain()

            print(f"{expo} {gain} {ret_code}")

            payload = {
            "getCCtrl_expo": expo,
            "getCCtrl_gain": gain
            }

            # Send camera control parameters to client
            qCU_Net.send_response_to_client(client_socket, payload)

            # Delete the camera control object
            del cameraCtrl

    # Check camera control parameter request
    if isinstance(json_payload, dict):
        if 'set_camCtrl' in json_payload:

            curExpo = json_payload['expo']
            curGain = json_payload['gain']

            # Initialize the camera control object
            cameraCtrl = qCU_CCtrl()

            # Get camera control parameters
            ret_code = cameraCtrl.set_expo_gain(curExpo, curGain)


            print(f"{curExpo} {curGain} {ret_code}")

            payload = {
            "set_camCtrl_status": ret_code
            }

            # Send camera control parameters to client
            qCU_Net.send_response_to_client(client_socket, payload)

            # Delete the camera control object
            del cameraCtrl



    # Check camera control parameter request
    if isinstance(json_payload, dict):
        if 'auto_camCtrl' in json_payload:
            isAutoCamCtrl = json_payload['auto_camCtrl']

            autoPeriodMs = json_payload.get('auto_period_ms')

            if isAutoCamCtrl == 1:
                # Start
                gAutoEG.start(data_func=get_latest_frame, interval_ms=autoPeriodMs)
            else:
                # Stop
                gAutoEG.stop()


def main():

    # Declara global variables
    global gQCUData
    global gAutoEG

    # Create the data interface
    gQCUData = qCUData()
    if not gQCUData.init():
        print("Failed to initialize shared memory")
        return

    # Initialize auto exposure gain with camera control parameters
    tmpCCtrl = qCU_CCtrl()
    camCtrlRanges = tmpCCtrl.get_cam_ctrl_ranges()
    print(f"Camera control ranges: {camCtrlRanges}")
    del tmpCCtrl
    #
    gAutoEG = AutoExposureGain(cctrl_ranges=camCtrlRanges, target_brightness=128, tolerance=10, adjustment_factor=0.5)


    qCU_Net.start_tcp_server(host='192.168.10.55', port=12345, json_handler=enc_json_handler)


if __name__ == "__main__":
    print("qCU_Net Server Usage")
    print("====================================")

    # Run different examples
    main()
