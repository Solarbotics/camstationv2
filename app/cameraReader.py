"""Provide the PiCamera as a Reader."""

import dataclasses
import logging
import typing as t

import cv2
import numpy
import picamera
from picamera.array import PiRGBArray

from . import reader

Image = t.Union[numpy.ndarray]

T = t.TypeVar("T")
V = t.TypeVar("V")

class ImageProcessor(t.Generic[T, V]):

    def process_frame(self, source: Image, **options: V) -> t.Tuple[Image, T]:
        """Abstract method."""
        raise NotImplementedError


@dataclasses.dataclass()
class Camera(reader.ReaderContext[Image]):
    """Class that manages collecting images."""

    camera: picamera.PiCamera

    def __post_init__(self) -> None:
        """Perform non-dataclass init."""
        self.capture = PiRGBArray(self.camera)
        self.generator = self.camera.capture_continuous(
            self.capture, format="bgr", use_video_port=True
        )

    def close(self) -> None:
        """Close the Camera and composed objects."""
        self.camera.close()

    def read(self) -> Image:
        """Read a processed image and values from the camera."""
        next(self.generator)
        # Extract the numpy frame
        frame = self.capture.array.copy()
        # logger.debug("Inside generator: %s", cls.frame)
        # Truncate so capture can be reused
        self.capture.truncate(0)
        return frame
