"""Methods for measuring (the height of) the product."""

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

logger = logging.Logger(__name__)
logger.addHandler(logging.NullHandler())


class Reporter:
    """Base class that can report a distance and height.

    Can be used as a context manager,
    although this base implementation does nothing with the context.
    """

    def read(self) -> int:
        """Method to be overridden."""
        raise NotImplementedError

    def height(self, base_depth: int = 0) -> int:
        """Calculate the height of a sensed object.

        Assumes the object to be sitting on a surface `base_depth` units aways,
        and calculates height = base_depth - object_depth.

        Gets the depth of the object from a read.
        """
        return base_depth - self.read()

    def close(self) -> None:
        """Close the Reporter.

        Implementations may have actual behaviour here.
        """

    def __enter__(self) -> "Reporter":
        """Create context manager view, i.e. self."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context by closing this Reporter."""
        self.close()


class Sensor(Reporter):
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
        """Read the unit distance sensed.

        Most likely millimetres.
        """
        distance = self.tof.get_distance()
        return distance

    def close(self) -> None:
        """Close the sensor."""
        self.tof.stop_ranging()
        self.tof.close()


def _default_sensor() -> Sensor:
    """Construct the default sensor.

    Controlled by config values.
    """
    tof = VL53L0X.VL53L0X(
        i2c_bus=config.measure.bus, i2c_address=config.measure.address
    )
    sensor = Sensor(tof, level=config.measure.range)
    return sensor


class ThreadedSensor(Reporter):
    """Lazily maintains a single thread running a default Sensor."""

    IDLE_TIME = 10

    thread: t.Optional[threading.Thread] = None
    last_access: float = 0
    distance: t.Optional[int] = None

    @classmethod
    def operate(cls) -> None:
        """Create and continually read a Sensor."""
        with _default_sensor() as sensor:
            logger.info("Opened VL53LXX sensor.")
            while time.time() - cls.last_access > cls.IDLE_TIME:
                cls.distance = sensor.read()

    @classmethod
    def start(cls) -> None:
        """Start a new thread if neccesary."""
        if cls.thread is None:
            logger.info("Starting distance sensor thread.")
            cls.thread = threading.Thread(target=cls.operate)
            cls.thread.start()

    @classmethod
    def read(cls) -> int:
        """Obtain the last read distance value."""
        cls.last_access = time.time()
        cls.start()
        while cls.distance is None:
            logger.debug("Waiting for distance.")
            time.sleep(0)
        return cls.distance


def default_sensor() -> Reporter:
    """Return a reporter."""
    return ThreadedSensor()

    # default_sensor = _default_sensor


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
