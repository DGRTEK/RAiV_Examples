import qCU_PinBus
#import time
import threading

leftPinNo = 0
rightPinNo = 1
#
frwdPwmN0 = 1
bckdPwmN0 = 0

def main():

    event = threading.Event()

    # Test GPOUT Write
    pinNo = leftPinNo
    pinVal = 1
    status = qCU_PinBus.gpout_write(pinNo, pinVal)
    print(f"gpout_write status {status}")

    #time.sleep(0.05)
    event.wait(0.05)

    pinNo = leftPinNo
    pinVal = 0
    status = qCU_PinBus.gpout_write(pinNo, pinVal)
    print(f"gpout_write status {status}")


    #time.sleep(0.25)
    event.wait(0.25)

    pinNo = rightPinNo
    pinVal = 1
    status = qCU_PinBus.gpout_write(pinNo, pinVal)
    print(f"gpout_write status {status}")

    #time.sleep(0.05)
    event.wait(0.05)

    pinNo = rightPinNo
    pinVal = 0
    status = qCU_PinBus.gpout_write(pinNo, pinVal)
    print(f"gpout_write status {status}")


    #time.sleep(0.25)
    event.wait(0.25)

    # Test PWM Write
    pinNo = frwdPwmN0
    periodMs= 1000
    dutyMs= 850
    status = qCU_PinBus.pwm_write(pinNo, periodMs, dutyMs)
    print(f"pwm_write status {status}")

    #time.sleep(1.25)
    event.wait(1.25)

    pinNo = frwdPwmN0
    periodMs= 1000
    dutyMs= 1000    # For RAiV v1.0 there is no pwm disable
    status = qCU_PinBus.pwm_write(pinNo, periodMs, dutyMs)
    print(f"pwm_write status {status}")


    #time.sleep(0.25)
    event.wait(0.25)

    # Test PWM Write
    pinNo = bckdPwmN0
    periodMs= 1000
    dutyMs= 800
    status = qCU_PinBus.pwm_write(pinNo, periodMs, dutyMs)
    print(f"pwm_write status {status}")

    #time.sleep(1.25)
    event.wait(1.25)

    pinNo = bckdPwmN0
    periodMs= 1000
    dutyMs= 1000    # For RAiV v1.0 there is no pwm disable
    status = qCU_PinBus.pwm_write(pinNo, periodMs, dutyMs)
    print(f"pwm_write status {status}")



if __name__ == "__main__":
    print("qCU_PinBus Usage")
    print("====================================")

    # Run different examples
    main()
