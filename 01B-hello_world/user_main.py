import qCU_Print


def main():

    # Print to stdout only
    print("Hello World")

    # Enable back panel USB serial port
    qCU_Print.qcu_print_enable('/dev/ttyS4')

    # Print to stdout and ttyS4
    print("Hello World to USB too")

    # Disable back panel USB serial port
    qCU_Print.qcu_print_disable()

    # Print to stdout only
    print("Hello World again stdout")

if __name__ == "__main__":
    main()
