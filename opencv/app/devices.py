"""Construct and manage persistant external devices."""

import logging

import numpy
import serial
import VL53L0X

from . import camera
from . import config
from . import measure
from . import reader
from . import scale

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# Camera methods and objects


# Load calibration matrices
camera_matrix = numpy.loadtxt(config.process.cameraMatrix, dtype="float", delimiter=",")
scale_matrix = numpy.loadtxt(
    config.process.cameraScaleMatrix, dtype="float", delimiter=","
)
camera_matrix *= scale_matrix
distortion_matrix = numpy.loadtxt(
    config.process.cameraDistortionMatrix, dtype="float", delimiter=","
)


def get_camera() -> camera.Camera:
    """Get the camera."""
    return camera.Camera(
        processor=camera.ImageSizer(
            cam_matrix=camera_matrix, dist_coeffs=distortion_matrix
        )
        # processor=camera.ImageProcessor()
    )


# Scale methods and object


def _default_scale() -> scale.Scale:
    """Construct a default Scale."""
    device = serial.Serial(
        port=config.scale.port,
        baudrate=config.scale.baudrate,
        timeout=config.scale.timeout,
    )
    sc = scale.Scale(device, pause=config.scale.pause)
    return sc


# Construct a single (threaded) scale
threaded_scale = scale.ThreadedScale(
    _default_scale, timeout=config.readers.inactivity_timeout
)


def get_scale() -> reader.Device[float]:
    """Return a constant Scale manager."""
    return threaded_scale


# Sensor methods and object


def _default_sensor() -> measure.Sensor:
    """Construct the default sensor.

    Controlled by config values.
    """
    tof = VL53L0X.VL53L0X(
        i2c_bus=config.measure.bus, i2c_address=config.measure.address
    )
    sensor = measure.Sensor(tof, level=config.measure.range)
    logger.info("Opened VL53LXX sensor.")
    return sensor


# Construct a single sensor
measure_sensor = measure.ThreadedSensor(
    _default_sensor, timeout=config.readers.inactivity_timeout
)


def get_sensor() -> reader.Device[float]:
    """Return a sensor."""
    return measure_sensor
