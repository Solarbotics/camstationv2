"""Interact with the weighing scale.

Interacting with the serial port requires being in the dialout group.
"""

# import re
import contextlib
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

# TODO consider moving the scale to a seperate thread
class Scale:
    """Generically receive weight data."""

    scale: t.Optional[serial.Serial] = None

    def open(self) -> None:
        """Open scale the scale if neccesary."""
        if self.scale is None:
            self.scale = serial.Serial(port=COM_PORT, baudrate=COM_BAUDRATE, timeout=TIMEOUT)
            self.unlock()
            # scale.is_open()
            logger.debug("Opened scale: %s", self.scale)

    def close(self) -> None:
        """Close scale."""
        if self.scale is not None:
            self.scale.close()

    def unlock(self) -> None:
        """Update lock time for safety."""
        self.lock_time = time.time() + config.scale.pause

    def wait(self) -> None:
        """Wait enough time for the scale to be ready to be messaged."""
        current = time.time()
        if current < self.lock_time:
            logger.debug("Sleeping %s", self.lock_time - current)
            time.sleep(self.lock_time - current)

    def self(self) -> None:
        """Tare the scale."""
        self.open()
        self.wait()

        logger.info("Taring scale")
        self.scale.write(b'x1x')  # Open menu; tare, close menu
        logger.info("Tare complete")

        self.unlock()

    def read(self) -> float:
        """Read weight from the scale."""
        self.open()
        self.wait()

        logger.info("Reading scale")
        # b'r' seems to be the read signal
        self.scale.reset_input_buffer()
        self.scale.write(b'r')
        # was working before flush but might as well
        self.scale.flush()
        # upon proper behaviour, get like "0.000,kg,\r\n" 
        scaleData = self.scale.readline().decode("ascii").split(',')
        logger.info("Scaledata: %s", scaleData)
        self.unlock()
        return scaleData[0]      


    def __init__(self) -> None:
        """Initiate a view to the scale."""
        self.lock_time: float = 0

@contextlib.contextmanager
def managed_scale() -> t.Generator[Scale, None, None]:
    """Return a context-manager version of a Scale."""
    scale = Scale()
    try:
        yield scale
    finally:
        scale.close()

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

