import qCU_Net

def main():

    print("**** TCP Client ****")

	# Define Payload of the TCP message
    payload = {
        "text": "Hello Net Comm"
    }
    # Send the Payload (the message header is computed inside the function)
    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

if __name__ == "__main__":
    main()
