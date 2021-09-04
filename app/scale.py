"""Interact with the weighing scale.

Interacting with the serial port requires being in the dialout group.
"""

# import re
import logging
import serial

# import sys
import time
import typing as t

from . import reader

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TaredReader(reader.Obtainer[float]):
    """Mixin that provides a .obtain method.

    Returns the difference between the provided base and the read value.
    """

    def read(self) -> float:
        raise NotImplementedError

    def obtain(self, base: float) -> float:
        """Read the calculated weight, based on provided base tare."""
        return self.read() - base


class Scale(reader.ReaderContext[float], TaredReader):
    """Generically receive weight data."""

    def __init__(self, device: serial.Serial, *, pause: float = 0) -> None:
        """Initiate a view to the scale.

        Scale operations will wait a minimum of `pause` seconds
        between IO operations."""
        self.device: serial.Serial = device
        self.lock_time: float = 0
        self.pause = pause

        self.tare_amount: float = 0

        self.unlock()

    def unlock(self) -> None:
        """Update lock time."""
        self.lock_time = time.time() + self.pause

    def wait(self) -> None:
        """Wait enough time for the underlying device to be safely used."""
        current = time.time()
        if current < self.lock_time:
            logger.debug("Sleeping %s", self.lock_time - current)
            time.sleep(self.lock_time - current)

    def _device_tare(self) -> None:
        """Tare the scale.

        THIS METHOD IS DEPRECEATED;
        Taring is more quickly and reliably done client side.
        """
        self.wait()

        self.device.reset_input_buffer()

        logger.debug("Taring scale")
        self.device.write(b"x1x")  # Open menu; tare, close menu
        logger.debug("Tare complete")

        self.unlock()

    # TODO NOT THREADSAFE
    def tare(self) -> None:
        """Tare this scale object.

        The tare is only maintained in-code,
        not on the device itself.
        """
        self.tare_amount = self.read()

    def read(self) -> float:
        """Read weight from the scale."""
        self.wait()
        logger.debug("Reading scale")

        # b'r' seems to be the read signal
        self.device.reset_input_buffer()
        self.device.write(b"r")
        # was working before flush but might as well
        self.device.flush()

        # upon proper behaviour, get like "0.000,kg,\r\n"
        scaleData = self.device.readline().decode("ascii").split(",")
        self.unlock()
        logger.debug("Scaledata: %s", scaleData)

        try:
            value = float(scaleData[0])
        except (ValueError, IndexError):
            logger.error("Could not obtain value from scale data.")
            value = 0
        return value - self.tare_amount

    def close(self) -> None:
        """Close the serial."""
        self.device.close()


class ThreadedScale(reader.ThreadedReader[float], TaredReader, reader.Device[float]):
    """Combination of a ThreadedReader[float] and a TaredReader."""
