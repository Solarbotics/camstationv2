"""Testing the distance sensor."""

import collections
import logging
import signal
import typing as t

import VL53L1X

root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s")
)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

running = True


def main() -> None:
    """Main function."""
    global running

    tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)

    tof.open()

    tof.set_user_roi(VL53L1X.VL53L1xUserRoi(6, 9, 9, 6))
    tof.set_timing(100_000, 105)

    tof.start_ranging(mode=VL53L1X.VL53L1xDistanceMode.SHORT)

    logger.info(tof.get_timing())

    history: t.Deque[int] = collections.deque(maxlen=7)

    running = True

    while running:
        distance = tof.get_distance()
        history.append(distance)
        average = sorted(history)[len(history) // 2]
        logger.info("Average: %smm, (%smm)", average, distance)

    tof.stop_ranging()
    tof.close()
    print()


def exit_handler(signal, frame) -> None:
    global running
    running = False


signal.signal(signal.SIGINT, exit_handler)

if __name__ == "__main__":
    main()
