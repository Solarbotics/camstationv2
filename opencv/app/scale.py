"""Interact with the weighing scale.

Interacting with the serial port requires being in the dialout group.
"""

# import re
import logging
import serial
# import sys
import time
import typing as t

from . import config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# comport = 'com4'
COM_PORT = config.scale.port
COM_BAUDRATE = config.scale.baudrate
TIMEOUT = config.scale.timeout # seconds
# weight = 0


# Upon retrospect, "initscale" isn't that necessary up front. It just lets us bring up and manipulate the startup
# Until otherwise configured, we need to ensure:
# 3. Timestamp: off
# 6. Units: KG
# t. Serial trigger: ON
# c. Trigger character: 'r' (r = readval)
# def initscaleOld():
#     print("Initializing Scale")
#     scale.flush()
#     scaledefaults = []
#     time.sleep(3)
#     scale.write(b'x')  # Open Menu
#     stopflag = True
#     while stopflag:
#         raw = scale.readline().decode().splitlines()
#         # print("val:", raw)
#         scaledefaults.append(raw[0])
#         if 'x)' in raw[0]:
#             stopflag = False
#     print(*scaledefaults, sep="\n")  # '*' means there could be more than one object

#     # Let's try to pull out a setting, i.e. make sure '6' is in kg, not lbs.
#     defaulttype = [i for i in scaledefaults if i.startswith('6)')]
#     print("defaulttype: ", defaulttype)
#     result = re.search('\[(.*)\]', defaulttype[0]).group(1)
#     print("result: ", result)


def new_scale() -> serial.Serial:
    """Construct and return a new scale Serial.
    
    Should be used as a context manager.
    """
    scale = serial.Serial(port=COM_PORT, baudrate=COM_BAUDRATE, timeout=TIMEOUT)
    # scale.is_open()
    logger.debug("Opened scale: %s", scale)
    return scale


def tare(scale: serial.Serial):
    """Tare the given scale."""
    logger.info("Taring scale")
    # scale.flush() # flushs write data, not sure why needed
    # time.sleep(2) # ???
    scale.write(b'x1x')  # Open menu; tare, close menu
    # time.sleep(4)
    logger.info("Tare complete")


def read_weight(scale: serial.Serial) -> float:
    """Read the current weight on the scale."""
    logger.info("Reading scale")
    # b'r' seems to be the read signal
    scale.reset_input_buffer()
    scale.write(b'r')
    # was working before flush but might as well
    scale.flush()
    # upon proper behaviour, get like "0.000,kg,\r\n" 
    scaleData = scale.readline().decode("ascii").split(',')
    logger.info("Scaledata: %s", scaleData)
    return scaleData[0]
    # time.sleep(0.1)

# TODO consider moving the scale to a seperate thread
class Scale:
    """Generically receive weight data."""

    scale: t.Optional[serial.Serial] = None
    
    lock_time: float = 0

    @classmethod
    def initiate(cls) -> None:
        """Initiate scale."""
        if cls.scale is None:
            cls.scale = serial.Serial(port=COM_PORT, baudrate=COM_BAUDRATE, timeout=TIMEOUT)
            cls.unlock()
            # scale.is_open()
            logger.debug("Opened scale: %s", cls.scale)

    @classmethod
    def close(cls) -> None:
        """Close scale."""
        if cls.scale is not None:
            cls.scale.close()

    @classmethod
    def unlock(cls) -> None:
        """Update lock time for safety."""
        cls.lock_time = time.time() + config.scale.pause

    @classmethod
    def wait(cls) -> None:
        """Wait enough time for the scale to be ready to be messaged."""
        current = time.time()
        if current < cls.lock_time:
            logger.debug("Sleeping %s", cls.lock_time - current)
            time.sleep(cls.lock_time - current)

    @classmethod
    def tare(cls) -> None:
        """Tare the scale."""
        cls.initiate()
        cls.wait()

        logger.info("Taring scale")
        cls.scale.write(b'x1x')  # Open menu; tare, close menu
        logger.info("Tare complete")

        cls.unlock()

    @classmethod
    def read(cls) -> float:
        """Read weight from the scale."""
        cls.initiate()
        cls.wait()

        logger.info("Reading scale")
        # b'r' seems to be the read signal
        cls.scale.reset_input_buffer()
        cls.scale.write(b'r')
        # was working before flush but might as well
        cls.scale.flush()
        # upon proper behaviour, get like "0.000,kg,\r\n" 
        scaleData = cls.scale.readline().decode("ascii").split(',')
        logger.info("Scaledata: %s", scaleData)
        cls.unlock()
        return scaleData[0]      


    def __init__(self) -> None:
        """Initiate a view to the scale."""

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # with new_scale() as scale:
    #     # time.sleep(3)
    #     tare(scale)
    #     # 3 doesn't seem to be required
    #     # lower usually works (like 2.x)
    #     # but 3 seems to always work
    #     # time.sleep(3) # neccesary
    #     print(read_weight(scale))
    scale = Scale()
    scale.tare()
    scale.read()
    scale.close()

