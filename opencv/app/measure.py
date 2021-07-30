"""Methods for measuring (the height of) the product."""

import contextlib
import logging
import signal
import time
import typing as t

# import smbus2
# import VL53L1X
import VL53L0X

from . import config

logger = logging.Logger(__name__)
logger.addHandler(logging.NullHandler())


class Sensor:
    """Construct a distance sensor."""

    def __init__(self, tof: VL53L0X.VL53L0X, level: int = 1) -> None:
        """Construct a new Sensor based on an unopened ToF VL53LXX."""
        self.tof = tof
        self._open(level)

    def _open(self, level: int = 1) -> "Sensor":
        self.tof.open()
        self.tof.start_ranging(level)
        return self

    def read(self) -> int:
        """Read the distance sensed."""
        distance = self.tof.get_distance()
        return distance

    def close(self) -> None:
        """Close the sensor."""
        self.tof.stop_ranging()
        self.tof.close()

    def __enter__(self) -> "Sensor":
        """Create context manager view, i.e. self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context, closing the sensor."""
        self.close()


def default_sensor() -> Sensor:
    """Construct the default sensor.

    Controlled by config values.
    """
    tof = VL53L0X.VL53L0X(
        i2c_bus=config.measure.bus, i2c_address=config.measure.address
    )
    sensor = Sensor(tof, level=config.measure.range)
    return sensor


def main() -> None:
    """Continously read distance from the sensor."""

    # Setup logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Construct ToF and sensor object
    sensor = default_sensor()

    # Nasty little mutable high scope boolean
    # but less nasty than using `global`
    running = [True]

    # SIGINT handler
    def shutdown(signal: signal.Signals, frame) -> None:
        running[0] = False
        sensor.close()
        logger.info("Cleaned up.")

    signal.signal(signal.SIGINT, shutdown)

    # Main loop, periodically read and log data
    while running[0]:
        data = sensor.read()
        logger.info(data)
        time.sleep(0.2)


if __name__ == "__main__":
    main()

# https://github.com/kplindegaard/smbus2
# https://solarbotics.com/product/51112/
# https://www.st.com/resource/en/datasheet/vl53l1x.pdf
# https://shop.pimoroni.com/products/vl53l1x-breakout
# https://github.com/pimoroni/vl53l1x-python
