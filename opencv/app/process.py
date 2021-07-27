"""Operate main camera station processes."""

import base64
import json
import typing as t

import cv2
import numpy

from . import camera
from . import config
from . import files
from . import lights
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


def activate(*args: t.Any, **kwargs: t.Any) -> t.Mapping[str, object]:
    """Activate a round of the camera station."""
    # Turn on lights
    lights.Lights().ring().on()
    # Operate undercamera for sizing
    sizes = get_camera().get_processed_frame(threshold=kwargs.get("threshold", None))[1]
    size = sizes[0]
    # Turn off lights
    lights.Lights().ring().off()
    # Use overhead tech to get depth
    # Read scale
    try:
        with scale.managed_scale() as sc:
            weight = sc.read()
    except Exception:
        weight = 0
    # Save gathered data
    file_name = files.data_name(
        name=config.process.data_name,
        folder=config.process.paths.data,
        extension="json",
        timestamp=True,
    )
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump({"size": size, "weight": weight}, f)
    # Take photos
    photo_paths = photo.capture_image_set(config.process.paths.photos)
    # Encode and return pictures
    # Return data
    encoded_images = [
        base64.b64encode(cv2.imread(path).imencode("jpg").tobytes())
        for path in photo_paths
    ]
    return {
        "message": "success",
        "size": size,
        "weight": weight,
        "photos": encoded_images,
    }
