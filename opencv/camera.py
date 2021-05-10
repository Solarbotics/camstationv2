"""Handles video collection and processing"""

import typing as t

import cv2
import numpy

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
    """Parses the given source image for bounding boxes.

    Returns the highlighted image and the width and height of the bounding box.
    """
    # Copy original image for output
    output = source.copy()
    # list of sizes of contour boxes
    sizes = []

    # Apply a blur effect to reduce noise
    blurred = cv2.blur(source, (6 * 50 + 1, 6 * 50 + 1), 50)
    # Convert to HSV
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    # Filter based on value
    hue_range = (0.0, 180.0)
    sat_range = (0.0, 255.0)
    value_range = (0.0, 80.0)
    threshed = cv2.inRange(hsv, *zip(hue_range, sat_range, value_range))
    # Find contours
    contours, _ = cv2.findContours(
        threshed, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
    )
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
        self.frames = [cv2.imread("test.jpg")]


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
