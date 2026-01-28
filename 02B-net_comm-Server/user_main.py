# Module for TCP communication
import qCU_Net

# Sample implementation of a json payload handler 
def sample_json_handler(client_socket, json_payload, client_address):
    print(f"Custom handler called for client {client_address}")
    print(f"Received payload: {json_payload}")

def main():

    print("**** TCP Server ****")

	# Start the TCP server with sample json handler
    qCU_Net.start_tcp_server(host='192.168.10.55', port=12345, json_handler=sample_json_handler)

if __name__ == "__main__":
    main()
