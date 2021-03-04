import configparser
import serial
import multiprocessing

## Change this to match your local settings
# SERIAL_PORT = '/dev/ttyUSB0'
# SERIAL_BAUDRATE = 9600
config = configparser.ConfigParser()
config.read('/home/dave/PycharmProjects/camstationv2/camstation.cfg')
SERIAL_PORT = config.get("CAMSCALE", 'comport')
SERIAL_BAUDRATE = config.get("CAMSCALE", 'combaud')

class SerialProcess(multiprocessing.Process):

    def __init__(self, input_queue, output_queue):
        multiprocessing.Process.__init__(self)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.sp = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)

    def close(self):
        self.sp.close()

    def writeSerial(self, data):
        self.sp.write(data.encode())
        # time.sleep(1)

    def readSerial(self):
        # return self.sp.readline().replace("\n", "")
        # val = self.sp.readline().decode().split(',')[0]
        # print("Val",val)
        return self.sp.readline().decode().split(',')[0]

    def run(self):

        self.sp.flushInput()

        while True:
            # look for incoming tornado request
            if not self.input_queue.empty():
                data = self.input_queue.get()

                # send it to the serial device
                self.writeSerial(data)
                print("writing to serial: ", data)

            # look for incoming serial data
            if self.sp.inWaiting() > 0:
                data = self.readSerial()
                # print("reading from serial: ", data)
                # send it back to tornado
                self.output_queue.put(data)
