"""Operate main camera station processes."""

import json
import typing as t

import numpy

from . import camera
from . import config
from . import files
from . import photo
from . import scale

# Load calibration matrices
camera_matrix = numpy.loadtxt("cameraMatrix.txt", dtype="float", delimiter=",")
scale_matrix = numpy.loadtxt("cameraScaleMatrix.txt", dtype="float", delimiter=",")
camera_matrix *= scale_matrix
distortion_matrix = numpy.loadtxt("cameraDistortion.txt", dtype="float", delimiter=",")


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


def activate(*args: t.Any, **kwargs: t.Any) -> str:
    """Activate a round of the camera station."""
    # Operate undercamera for sizing
    sizes = get_camera().get_processed_frame(threshold=kwargs.get("threshold", None))[1]
    size = sizes[0]
    # Use overhead tech to get depth
    # Read scale
    with scale.managed_scale() as sc:
        weight = sc.read()
    file_name = (
        files.data_name(
            name=config.process.data_name,
            folder=config.process.paths.data,
            extension="json",
            timestamp=True,
        ),
    )
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump({"size": size, "weight": weight}, f)
    # Take photos
    photo.capture_image_set(config.process.paths.photos)
    return "X"
