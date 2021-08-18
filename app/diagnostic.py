"""Command line tool to run various diagnostics / testing on the station."""

import logging
import signal
import time

from . import devices

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def main() -> None:
    """Continously read distance from the sensor."""

    # Setup logger
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Construct ToF and sensor object
    _sensor = devices.get_sensor()

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
