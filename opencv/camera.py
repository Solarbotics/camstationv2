"""Handles video collection and processing"""

import time
import typing as t

import cv2
import numpy
import picamera
from picamera.array import PiRGBArray

# import imutils

# Minor typing restriction, far from sound but better than nothing
Image = numpy.ndarray


def scale(image: Image, factor: float = 1) -> Image:
    """Scales an image by the given factor.

    Scales in both axes to preserve aspect ratio.
    """
    return cv2.resize(image, (0, 0), fx=factor, fy=factor, interpolation=cv2.INTER_AREA)


# https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_image_display/py_image_display.html


def process_frame(source: Image) -> t.Tuple[Image, t.Sequence[t.Tuple[int, int]]]:
    """Process the given source image,
    resizing and modifying it, searching for bounding boxes.

    Returns the highlighted image and the width and height of the bounding box.
    """

    # list of sizes of contour boxes
    sizes = []

    # pipeline:
    # crop (?)
    # copy for output
    # blur
    # filter (hsv)
    # find contours

    def cropped(image: Image) -> Image:
        """Crop step"""
        yMargin = 50
        leftMargin = 450
        rightMargin = 500
        return image[yMargin:-yMargin, leftMargin:-rightMargin].copy()

    def blurred(image: Image) -> Image:
        """Applies blur step"""
        return cv2.blur(image, (6 * 50 + 1, 6 * 50 + 1), 50)

    def hsv_filtered(image: Image) -> Image:
        """Applies HSV filtering step.

        Expets BGR Image.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Filter based on value
        hue_range = (0.0, 180.0)
        sat_range = (0.0, 255.0)
        value_range = (0.0, 80.0)
        return cv2.inRange(hsv, *zip(hue_range, sat_range, value_range))

    def contours_of(image: Image) -> numpy.ndarray:
        """Contour finding step.

        Expects single channel Image.
        """
        contours, _ = cv2.findContours(
            image, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
        )
        # print(contours)
        return contours

    cropped_image = cropped(source)
    output = cropped_image.copy()
    contours = contours_of(hsv_filtered(blurred(cropped_image)))

    # Parse contours
    for contour in contours:
        # flatrect =cv2.boundingRect(contour)
        # https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
        rect = cv2.minAreaRect(contour)
        # print(rect)
        box = numpy.int0(cv2.boxPoints(rect))

        red = (0, 0, 255)
        highlight_color = red
        highlight_thickness = 8
        cv2.drawContours(output, [box], 0, highlight_color, highlight_thickness)

        sizes.append(rect)

    return (output, sizes)


class Camera:
    """Class to generically provide camera frames."""

    def __init__(self) -> None:

        # Initialize camera
        self.camera = picamera.PiCamera()
        self.camera.framerate = 32
        self.capture = PiRGBArray(self.camera)

        self.generator = self.camera.capture_continuous(
            self.capture, format="bgr", use_video_port=True
        )

        # Wait for camera to warm up
        WARMUP_TIME = 0.1  # seconds
        time.sleep(WARMUP_TIME)

    def get_frame(self) -> Image:
        """Returns the raw image currently provided by the camera"""
        # Capture from camera
        # self.camera.capture(self.capture, format="bgr")
        # camera.capture_continuous(self.capture, format="bgr")
        # https://picamera.readthedocs.io/en/release-1.13/api_camera.html#picamera.PiCamera.capture_continuous

        # Truncate existing capture
        self.capture.truncate(0)
        # Step continuous capture
        next(self.generator)
        # Return array component
        return self.capture

    def get_processed_frame(self) -> Image:
        """Returns the current frame of the processed video"""
        return process_frame(self.get_frame())[0]

    def get_jpg(self) -> bytes:
        """Returns the current frame, encoded as jpg"""
        return cv2.imencode(".jpg", self.get_processed_frame())[1].tobytes()


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/


def main() -> None:
    """Main function"""
    source = cv2.imread("test.jpg")

    out, boxes = process_frame(source)

    print(boxes)

    cv2.imshow("output", scale(out, 0.125))
    cv2.waitKey(60 * 1000)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
