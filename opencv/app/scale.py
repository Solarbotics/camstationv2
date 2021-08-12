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
TIMEOUT = config.scale.timeout  # seconds
# weight = 0

# TODO consider moving the scale to a seperate thread
class Scale:
    """Generically receive weight data."""

    scale: t.Optional[serial.Serial] = None
    lock_time: float = 0

    @classmethod
    def open(cls) -> serial.Serial:
        """Open the scale if neccesary, and return it.

        Consecutive calls should return the same scale object,
        unless the previous scale was closed in between.
        """
        if cls.scale is None:
            cls.scale = serial.Serial(
                port=COM_PORT, baudrate=COM_BAUDRATE, timeout=TIMEOUT
            )
            cls.unlock()
            # scale.is_open()
            logger.debug("Opened scale: %s", cls.scale)
        return cls.scale

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
        scale = cls.open()
        cls.wait()

        scale.reset_input_buffer()

        logger.info("Taring scale")
        scale.write(b"x1x")  # Open menu; tare, close menu
        logger.info("Tare complete")

        cls.unlock()

    @classmethod
    def read(cls) -> float:
        """Read weight from the scale."""
        scale = cls.open()
        cls.wait()

        logger.info("Reading scale")
        # b'r' seems to be the read signal
        scale.reset_input_buffer()
        scale.write(b"r")
        # was working before flush but might as well
        scale.flush()
        # upon proper behaviour, get like "0.000,kg,\r\n"
        scaleData = scale.readline().decode("ascii").split(",")
        logger.info("Scaledata: %s", scaleData)
        cls.unlock()
        return scaleData[0]

    def __init__(self) -> None:
        """Initiate a view to the scale."""


global_scale = [None]


@contextlib.contextmanager
def managed_scale() -> t.Generator[Scale, None, None]:
    """Return a context-manager version of a Scale."""
    # scale = Scale()
    # try:
    #     yield scale
    # finally:
    #     scale.close()
    scale = Scale()
    try:
        yield scale
    finally:
        pass


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
