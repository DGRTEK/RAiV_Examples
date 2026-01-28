import qCU_Print
import qCU_Net
import qCU_Stream

def main():

    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    print("**** H264 Streaming Example ****")

    # Start TCP server
    qCU_Net.start_tcp_server(host='192.168.10.55', port=12345, json_handler=enc_json_handler)


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



if __name__ == "__main__":
    main()
