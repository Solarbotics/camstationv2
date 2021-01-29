# This is the first module to contribute to the CamStation v2.
# Let's get the SparkFun Openscale talk python
# Let's try to talk to the SparkFun Openscale module
import serial
import time
import re
import sys
comport = 'com4'
combaud = 9600
weight = 0



# Upon retrospect, "initscale" isn't that necessary up front. It just lets us bring up and manipulate the startup
# Until otherwise configured, we need to ensure:
# 3. Timestamp: off
# 6. Units: KG
# t. Serial trigger: ON
# c. Trigger character: 'r' (r = readval)
def initscale():
    print("Initializing Scale")
    scale.flush()
    scaledefaults = []
    time.sleep(3)
    scale.write(b'x')  # Open Menu
    stopflag = True
    while stopflag:
        raw = scale.readline().decode().splitlines()
        # print("val:", raw)
        scaledefaults.append(raw[0])
        if 'x)' in raw[0]:
            stopflag = False
    print(*scaledefaults, sep = "\n")   # '*' means there could be more than one object

    #Let's try to pull out a setting, i.e. make sure '6' is in kg, not lbs.
    defaulttype = [i for i in scaledefaults if i.startswith('6)')]
    print("defaulttype: ", defaulttype)
    result = re.search('\[(.*)\]', defaulttype[0]).group(1)
    print("result: ", result)


def tare():
    print("Taring Scale")
    #scale.flush()
    time.sleep(2)
    scale.write(b'x1x') # Open menu; tare, close menu
    time.sleep(4)
    print("Tare complete")

def readweight():
    scale.write(b'r')
    scale.flushInput()
    scaleData = scale.readline().decode('ascii').split(',')
    #print("Scaledata:",scaleData)
    return scaleData[0]
    time.sleep(0.1)

try:
    scale = serial.Serial(port=comport, baudrate=combaud, timeout=4)
    scale.isOpen()
    print("Scale Port",comport,"opened")
    tare()
    mass = readweight()

    time.sleep(2)
    mass = readweight()
    print(mass)
    time.sleep(2)
    mass = readweight()
    print(mass)
    time.sleep(2)
    mass = readweight()
    print(mass)
    time.sleep(2)
    mass = readweight()
    print(mass)
    time.sleep(2)
    mass = readweight()
    print(mass)


except serial.SerialException: # If port open, close and reopen
    print("Serial Exception:")
    print("Cannot connect to",comport)

