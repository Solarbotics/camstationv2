"""Control (ring) lights using GPIO.

Requires 'gpio' group for the user running the code.
"""

import logging

import gpiozero

from . import config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def construct_ring_light(pin: int) -> gpiozero.PWMOutputDevice:
    """Construct the ring lights device."""
    lights = gpiozero.PWMOutputDevice(pin)
    lights.off()
    return lights


class RingLights:
    """Class abstracting implementation of ring light control.
    
    Should not be externally constructed.
    """

    def __init__(self, device: gpiozero.PWMOutputDevice) -> None:
        """Construct new RingLights."""
        self.device = device

    def on(self) -> None:
        """Fully activate ring lights."""
        self.device.on()

    def off(self) -> None:
        """Fully deactivate ring lights."""
        self.device.off()

    @property
    def level(self) -> float:
        """Level (as [0, 1] float) of this ring lights."""
        return self.device.value

    @level.setter
    def level(self, value: float) -> None:
        """Set level (as [0, 1] float) of this ring lights."""
        self.device.value = value
        logger.info("Set lights to %s", value)


ring = RingLights(construct_ring_light(config.lights.pin))
