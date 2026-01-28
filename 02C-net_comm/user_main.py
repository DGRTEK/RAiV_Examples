import qCU_Print
import qCU_Net

def main():

    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    print("**** Net Comm Example ****")

    payload = {
        "text": "Hello Net Comm"
    }
    qCU_Net.send_data_to_server("192.168.10.2", 12345, payload)

if __name__ == "__main__":
    main()
