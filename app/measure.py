"""Methods for measuring (the height of) the product."""

import collections
import logging
import typing as t

# import VL53L0X
import VL53L1X

# sensor = VL53L1X.VL53L1X()
# sensor.set_user_roi()
# osensor = VL53L0X.VL53L0X()
# osensor.set_user_roi

from . import config
from . import reader

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class CalibratedSensor(reader.Obtainer[float]):
    """Mixin that provides a .obtain method.

    Returns the difference between the provided base and the read value.
    """

    def read(self) -> float:
        raise NotImplementedError

    def obtain(self, base: float) -> float:
        """Read the calibrated height, based on provided base height."""
        return base - self.read()


class Sensor(reader.ReaderContext[float], CalibratedSensor):
    """Construct a distance sensor."""

    def __init__(self, tof: VL53L1X.VL53L1X, level: int = 1) -> None:
        """Construct a new Sensor based on an opened (but not ranging) ToF VL53LXX."""
        self.tof = tof
        self._open(level)

    def _open(self, level: int = 1) -> "Sensor":
        """Open the sensor."""
        self.tof.start_ranging(level)
        return self

    def read(self) -> float:
        """Read the unit distance sensed.

        Should return centimeters with up to one decimal place.
        """
        distance = float(self.tof.get_distance()) * config.measure.cm_per_unit
        # logger.info("Distance: %s", distance)
        return distance

    def close(self) -> None:
        """Close the sensor."""
        self.tof.stop_ranging()
        self.tof.close()


class ThreadedSensor(
    reader.ThreadedReader[float], CalibratedSensor, reader.Device[float]
):
    """Maintain a seperate-threaded Sensor."""

    def post_init(self) -> None:
        """Perform post init logic.

        Initialize the rolling history window.
        """
        super().post_init()

        self.history: t.Deque[float] = collections.deque(
            maxlen=config.measure.sample_window
        )

    def get_value(self, reader: reader.Reader[float]) -> float:
        """Average the latest value over the rolling window."""
        self.history.append(reader.read())

        def format(list: t.Iterable[float]) -> str:
            return f'[{", ".join(f"{x:.1f}" for x in list)}]'

        return sorted(self.history)[len(self.history) // 2]
        # return sum(self.history) / len(self.history)


# https://github.com/kplindegaard/smbus2
# https://solarbotics.com/product/51112/
# https://www.st.com/resource/en/datasheet/vl53l1x.pdf
# https://shop.pimoroni.com/products/vl53l1x-breakout
# https://github.com/pimoroni/vl53l1x-python
