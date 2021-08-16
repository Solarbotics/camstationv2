"""Methods for measuring (the height of) the product."""

import collections
import logging
import typing as t

# import smbus2
# import VL53L1X
import VL53L0X

from . import config
from . import reader

logger = logging.Logger(__name__)
logger.addHandler(logging.NullHandler())


class CalibratedSensor(reader.Obtainer[int]):
    """Mixin that provides a .obtain method.

    Returns the difference between the provided base and the read value.
    """

    def read(self) -> int:
        raise NotImplementedError

    def obtain(self, base: int) -> int:
        """Read the calibrated height, based on provided base height."""
        return base - self.read()


class Sensor(reader.Reader[int], CalibratedSensor):
    """Construct a distance sensor."""

    def __init__(self, tof: VL53L0X.VL53L0X, level: int = 1) -> None:
        """Construct a new Sensor based on an unopened ToF VL53LXX."""
        self.tof = tof
        self._open(level)

    def _open(self, level: int = 1) -> "Sensor":
        """Open the sensor."""
        self.tof.open()
        self.tof.start_ranging(level)
        return self

    def read(self) -> int:
        """Read the unit distance sensed.

        Most likely millimetres.
        """
        distance = self.tof.get_distance()
        return distance

    def close(self) -> None:
        """Close the sensor."""
        self.tof.stop_ranging()
        self.tof.close()


class ThreadedSensor(reader.ThreadedReader[int], CalibratedSensor):
    """Maintain a seperate-threaded Sensor."""

    def post_init(self) -> None:
        """Perform post init logic.

        Initialize the rolling history window.
        """
        self.history: t.Deque[int] = collections.deque(
            maxlen=config.measure.sample_window
        )

    def get_value(self, reader: reader.Reader[int]) -> int:
        """Average the latest value over the rolling window."""
        self.history.append(reader.read())
        return round(sum(self.history) / len(self.history))

# https://github.com/kplindegaard/smbus2
# https://solarbotics.com/product/51112/
# https://www.st.com/resource/en/datasheet/vl53l1x.pdf
# https://shop.pimoroni.com/products/vl53l1x-breakout
# https://github.com/pimoroni/vl53l1x-python
