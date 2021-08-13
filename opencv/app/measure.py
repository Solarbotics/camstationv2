"""Methods for measuring (the height of) the product."""

import collections
import contextlib
import logging
import signal
import threading
import time
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


def _default_sensor() -> Sensor:
    """Construct the default sensor.

    Controlled by config values.
    """
    tof = VL53L0X.VL53L0X(
        i2c_bus=config.measure.bus, i2c_address=config.measure.address
    )
    sensor = Sensor(tof, level=config.measure.range)
    logger.info("Opened VL53LXX sensor.")
    return sensor


# Construct a single sensor
measure_sensor = ThreadedSensor(_default_sensor, timeout=3600)


def sensor() -> ThreadedSensor:
    """Return a sensor."""
    return measure_sensor


def main() -> None:
    """Continously read distance from the sensor."""

    # Setup logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Construct ToF and sensor object
    _sensor = sensor()

    # Nasty little mutable high scope boolean
    # but less nasty than using `global`
    running = [True]

    # SIGINT handler
    def shutdown(signal: signal.Signals, frame) -> None:
        running[0] = False
        _sensor.close()
        logger.info("Cleaned up.")

    signal.signal(signal.SIGINT, shutdown)

    # Main loop, periodically read and log data
    while running[0]:
        data = _sensor.read()
        logger.info(data)
        time.sleep(0.2)


if __name__ == "__main__":
    main()

# https://github.com/kplindegaard/smbus2
# https://solarbotics.com/product/51112/
# https://www.st.com/resource/en/datasheet/vl53l1x.pdf
# https://shop.pimoroni.com/products/vl53l1x-breakout
# https://github.com/pimoroni/vl53l1x-python
