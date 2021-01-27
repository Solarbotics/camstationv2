# Let's try to talk to the SparkFun Openscale module
import serial
import time
import re

comport = 'com4'
combaud = 9600
weight = 0

scale = serial.Serial(port=comport, baudrate=combaud, timeout=3)
def initscale2():
    print("Initializing Scale2")
    scale.flush()
    scaledefaults = []
    scale.write("x".encode())  # Open Menu
    time.sleep(1)
    while 1:
        raw = scale.readline()
        print(raw)
        data = raw.decode('ascii')
        # if ",lbs" in data or ",kg" in data:
        # scale.write("x".encode())  # Open Menu
        # time.sleep(1)
        print(data)

def initscale():
    print("Initializing Scale")
    scale.flush()
    scaledefaults = []
    time.sleep(2)
    scale.write(b'x')  # Open Menu
    # time.sleep(1)
    stopflag = True
    while stopflag:
        raw = scale.readline().decode().splitlines()
        # print("val:", raw)
        scaledefaults.append(raw[0])
        if 'x)' in raw[0]:
            stopflag = False
    print(scaledefaults)

    print(*scaledefaults, sep = "\n")   # '*' means there could be more than one object

    #Let's try to pull out a setting, i.e. make sure '6' is in kg, not lbs.
    defaulttype = [i for i in scaledefaults if i.startswith('6)')]
    print("defaulttype: ", defaulttype)
    result = re.search('\[(.*)\]', defaulttype[0]).group(1)
    print("result: ", result)




def tare():
    print("Taring Scale")
    scale.write("x".encode()) # Open Menu
    time.sleep(1)
    scale.write("1".encode()) # Trigger Tare
    time.sleep(3)
    scale.write("x".encode()) # Exit Menu

initscale()
