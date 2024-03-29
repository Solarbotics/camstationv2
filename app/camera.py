"""Handles video collection and processing"""

import dataclasses
import itertools
import logging
import threading
import time
import typing as t

import cv2
import numpy
import picamera
from picamera.array import PiRGBArray

from . import config

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# import imutils

T = t.TypeVar("T")


# Minor typing restriction, far from sound but better than nothing
Image = t.Union[numpy.ndarray]


def scale(image: Image, factor: float = 1) -> Image:
    """Scales an image by the given factor.

    Scales in both axes to preserve aspect ratio.
    """
    return cv2.resize(image, (0, 0), fx=factor, fy=factor, interpolation=cv2.INTER_AREA)


# https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_image_display/py_image_display.html


def crosshair(
    image: Image, radius: int, thickness: int, colour: t.Tuple[int, int, int]
) -> Image:
    """Draw a crosshair on the provided image.

    Does not mutate the provided argument.

    Note the actual line thickness is doubled.
    """
    image = image.copy()
    # print(image.shape)
    row_mid = (image.shape[0] // 2) - 1
    column_mid = (image.shape[1] // 2) - 1
    row_start = row_mid - (radius - 1)
    column_start = column_mid - (radius - 1)
    cv2.rectangle(
        image,
        (column_mid - (thickness - 1), row_start),
        (column_mid + thickness, row_start + (radius * 2 - 1)),
        colour,
    )
    cv2.rectangle(
        image,
        (column_start, row_mid - (thickness - 1)),
        (column_start + (radius * 2 - 1), row_mid + thickness),
        colour,
    )
    return image


class ImageProcessor:
    """Abstract class for objects capable of transforming an image."""

    def process_frame(self, source: Image, **options: t.Any) -> t.Tuple[Image, t.Any]:
        """Performs no processing, base method."""
        return (source, None)


@dataclasses.dataclass()
class ChessboardFinder(ImageProcessor):
    """Looks for an processes a chessboard."""

    points_width: int
    points_height: int

    def process_frame(
        self, source: Image, **options: t.Any
    ) -> t.Tuple[Image, t.Tuple[numpy.ndarray, bytes]]:
        """Searchs for chessboard."""

        ret, corners = cv2.findChessboardCorners(
            source, (self.points_height, self.points_width)
        )
        # ret, corners = True, []

        output = source

        if not ret:
            logger.debug("Failed")

        output = cv2.drawChessboardCorners(
            output, (self.points_height, self.points_width), corners, ret
        )

        # output = scale(output, factor=0.25)

        _, encoding = cv2.imencode(".jpg", output)

        return (output, (corners, encoding))


@dataclasses.dataclass()
class ImageSizer(ImageProcessor):
    """Handles processing a raw image.

    Constructed with various configuration numbers.
    """

    cam_matrix: numpy.ndarray
    dist_coeffs: numpy.ndarray

    def rect_to_size(
        self, rect: t.Tuple[object, t.Tuple[float, float], object]
    ) -> t.Tuple[float, float]:
        """Convert a rotated bounding rect to a scaled size."""
        # Pixel (corrected) to inches:
        # Sticky pad size:
        # 1 & 15/16 Inches = 1.9375 in
        # by 1 & 15/32 Inches = 1.46875 in
        # 233 by 168 pixels (approximate)
        # Ratio: 120.258 and 114.382 (not bad, not good)
        # pixels_per_centimeter = 1
        # pixels_per_centimeter = 85/8.255  # TODO approximate measure, should also look at arcuro?
        # PIXELS_PER_CENTIMETER = 82 / 8.255
        PIXELS_PER_CENTIMETER = 115 / 13
        return (rect[1][0] / PIXELS_PER_CENTIMETER, rect[1][1] / PIXELS_PER_CENTIMETER)

    def process_frame(
        self, source: Image, **options: t.Any
    ) -> t.Tuple[Image, t.Sequence[t.Tuple[float, float]]]:
        """Process the given source image,
        resizing and modifying it, searching for bounding boxes.

        Returns the highlighted image and the width and height of the bounding box.
        """

        # list of sizes of contour boxes
        sizes = []

        # pipeline:
        # crop (?)
        # copy for output
        # monoscale
        # deskew (or after blur?)
        # blur
        # filter (hsv)
        # find contours

        def corrected(image: Image) -> Image:
            """Correct distortion of the image."""
            # roi: region of interest
            newCamMatrix, roi = cv2.getOptimalNewCameraMatrix(
                self.cam_matrix,
                self.dist_coeffs,
                imageSize=(image.shape[1], image.shape[0]),
                alpha=0,
            )
            undistorted = cv2.undistort(
                image, self.cam_matrix, self.dist_coeffs, newCameraMatrix=newCamMatrix
            )
            # undistorted = cv2.undistort(image, self.cam_matrix, self.dist_coeffs)
            # x, y, width, height = roi
            # print(roi)
            # return undistorted[y:y+height, x:x+width]
            return undistorted

        def cropped(image: Image) -> Image:
            """Crop step"""
            leftMargin = 0
            rightMargin = 0  # 30
            topMargin = 0
            bottomMargin = 0
            return image[
                topMargin : (image.shape[0] - bottomMargin),
                leftMargin : (image.shape[1] - rightMargin),
            ].copy()

        def monoconvert(image: Image) -> Image:
            """Applies monoscale step"""
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        def blurred(image: Image) -> Image:
            """Applies blur step"""
            return cv2.blur(image, (5, 5))

        def thresholded(image: Image, upper: int = 0) -> Image:
            """Apply grayscale thresholding step.

            Expects single channel grayscale image.
            """
            _, thresh_output = cv2.threshold(image, upper, 255, cv2.THRESH_BINARY_INV)
            return thresh_output

        def contours_of(image: Image) -> numpy.ndarray:
            """Contour finding step.

            Expects single channel Image.
            """
            contours, _ = cv2.findContours(
                image, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
            )
            # print(contours)
            return contours

        corrected_image = corrected(source)
        # corrected_image = source #, need to recalibrate
        # can also probably scale cam properties by resolution scale
        # find what default resolution was and scale to the max
        cropped_image = cropped(corrected_image)
        mono = monoconvert(cropped_image)
        blur = blurred(mono)
        # blur = cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR)
        # filtered = hsv_filtered(blur)
        filtered = thresholded(blur, options["threshold"])
        contours = contours_of(filtered)

        # output = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
        # output = cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR)
        # output = corrected_image
        output = cropped_image.copy()
        overlay = numpy.zeros(output.shape, dtype=numpy.uint8)
        overlay[filtered > 0] = config.camera.colours.red
        # output[filtered > 0] = red
        output = cv2.addWeighted(output, 0.9, overlay, 0.1, gamma=0)

        # Parse contours
        MIN_SIZE = 10
        for contour in contours:
            # flatrect =cv2.boundingRect(contour)
            # https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
            rect = cv2.minAreaRect(contour)

            if rect[1][0] >= MIN_SIZE and rect[1][1] >= MIN_SIZE:
                # print(rect)
                box = numpy.int0(cv2.boxPoints(rect))

                highlight_color = config.camera.colours.blue
                highlight_thickness = config.camera.thickness
                text_color = config.camera.colours.green
                cv2.drawContours(output, [box], 0, highlight_color, highlight_thickness)
                cv2.putText(
                    output,
                    text="({0:.{prec}f}, {1:.{prec}f})".format(
                        *self.rect_to_size(rect), prec=2
                    ),
                    org=tuple(map(int, rect[0])),
                    fontFace=cv2.FONT_HERSHEY_PLAIN,
                    fontScale=1.0,
                    color=text_color,
                    thickness=1,
                )

                sizes.append(self.rect_to_size(rect))

        output = crosshair(
            output,
            radius=config.camera.crosshair.radius,
            thickness=config.camera.crosshair.thickness,
            colour=config.camera.colours.gray,
        )

        # print(sizes)

        display = output
        # display = source

        # back = numpy.full(source.shape, 0, dtype=numpy.uint8)
        # back[: output.shape[0], : output.shape[1]] = output
        # display = scale(numpy.concatenate((source, back), axis=1), factor=1)

        return (display, sizes)


def open_camera() -> picamera.PiCamera:
    """Open a properly configured PiCamera."""
    resolution = (320, 240)
    # resolution = (640, 480)
    # framerate = 32
    return picamera.PiCamera(resolution=resolution)


class Camera:
    """Class to generically provide camera frames."""

    # Time to wait before killing a thread
    IDLE_TIME: int = 10

    thread: t.Optional[threading.Thread] = None
    frame: t.Optional[Image] = None
    last_request: float = 0

    @classmethod
    def read_camera(cls) -> None:
        # Open camera in context manager for proper cleanup
        with open_camera() as camera:
            logger.info("Started PiCamera")

            # Wait for camera to warm up
            WARMUP_TIME = 2  # seconds
            # camera.start_preview()
            time.sleep(WARMUP_TIME)

            # Create PiRGBArray for cam output
            capture = PiRGBArray(camera)

            # Create a generator that will output into capture
            # on each iteration
            generator = camera.capture_continuous(
                capture, format="bgr", use_video_port=True
            )

            # We don't actually use the output of the generator
            for _ in generator:
                # Extract the numpy frame
                cls.frame = capture.array.copy()
                # logger.debug("Inside generator: %s", cls.frame)
                # Truncate so capture can be reused
                capture.truncate(0)
                # Break once there are no clients, stopping the thread
                if time.time() - cls.last_request > cls.IDLE_TIME:
                    break

        logger.info("Closed PiCamera.")
        # Remove this thread object from the class once it finishes
        cls.thread = None

    @classmethod
    def initialize(cls) -> None:
        """Initialize the camera."""
        # logger.debug("Inside initialize, thread: %s", cls.thread)
        # Start thread if it is not running
        if cls.thread is None:
            logger.debug("Creating thread")
            cls.thread = threading.Thread(target=cls.read_camera)
            cls.thread.start()
            # Busy wait until a frame is available
            while cls.frame is None:
                # Yield control
                time.sleep(0)
            # logger.debug("First frame: %s", cls.frame)

    @classmethod
    def get_frame(cls) -> Image:
        """Get the latest image frame."""
        cls.last_request = time.time()
        # logger.debug("Before initialize")
        cls.initialize()

        # logger.debug("Inside get_frame: %s", cls.frame)
        return cls.frame  # type: ignore

    def __init__(self, processor: ImageProcessor) -> None:

        # Save processor ref for use in getting frames
        self.processor = processor

    def get_processed_frame(self, **options: t.Any) -> t.Tuple[Image, t.Any]:
        """Returns the current frame of the processed video"""
        raw = type(self).get_frame()
        # logger.debug("Inside get_processed_frame: %s", raw)
        result = self.processor.process_frame(raw, **options)
        # logger.debug("Processed frame")
        return result

    def get_jpg(self, **options: t.Any) -> bytes:
        """Returns the current frame, encoded as jpg"""
        return cv2.imencode(".jpg", self.get_processed_frame(**options)[0])[1].tobytes()


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/


def main() -> None:
    """Main function"""
    source = cv2.imread("test.jpg")

    proc = ImageProcessor()
    out, result = proc.process_frame(source)

    print(result)

    cv2.imshow("output", scale(out, 0.125))
    cv2.waitKey(60 * 1000)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
