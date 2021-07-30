"""Operate main camera station processes."""

import base64
import json
import logging
import time
import typing as t

import cv2
import numpy

from . import camera
from . import config
from . import files
from . import lights
from . import measure
from . import photo
from . import scale

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

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
    # if "camera" in flask.g:
    #     return flask.g.camera
    # else:
    #     cam = camera.Camera(
    #         processor=camera.ImageSizer(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
    #         # processor=camera.ImageProcessor()
    #     )
    #     flask.g.camera = cam
    #     return cam
    return camera.Camera(
        processor=camera.ImageSizer(
            cam_matrix=camera_matrix, dist_coeffs=distortion_matrix
        )
        # processor=camera.ImageProcessor()
    )


def activate(*args: t.Any, **kwargs: t.Any) -> t.Mapping[str, object]:
    """Activate a round of the camera station."""
    # Turn on lights
    lights.Lights().ring().on()
    time.sleep(config.process.camera.wait)
    # Operate undercamera for sizing
    sizes = get_camera().get_processed_frame(threshold=kwargs.get("threshold", None))[1]
    size = tuple(f"{val:.2f}" for val in sizes[0])
    # Turn off lights
    lights.Lights().ring().off()
    # Use overhead tech to get depth
    try:
        with measure.default_sensor() as sensor:
            height = sensor.height(base_depth=kwargs.get("base_depth", 0))
    except Exception as e:
        logger.error(e)
        height = 0
    # Read scale
    try:
        with scale.managed_scale() as sc:
            weight = sc.read()
    except Exception as e:
        logger.error(e)
        weight = 0
    # Save gathered data
    file_name = files.data_name(
        name=config.process.data_name,
        folder=config.process.paths.data,
        extension="json",
        timestamp=True,
    )
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump({"size": size, "weight": weight, "height": height}, f)
    # Take photos
    try:
        photo_paths = photo.capture_image_set(config.process.paths.photos)
    except Exception as e:
        logger.error(e)
    # Encode and return pictures
    encoded_images: t.List[str] = [photo.encode_image(path) for path in photo_paths]
    # Return data
    return {
        "message": "success",
        "size": size,
        "weight": weight,
        "height": height,
        "photos": encoded_images,
    }
