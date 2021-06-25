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

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# import imutils

T = t.TypeVar("T")


def pipeline(
    source: T, transformations: t.Sequence[t.Callable[[T], T]]
) -> t.Iterable[T]:
    """Apply a sequence of transformations to a starting value.

    Returns each intermediate result in a sequence,
    in the same order as the transformations were applied.

    Returns source as the first element of the iterable.
    """
    return itertools.accumulate(transformations, func=lambda a, f: f(a), initial=source)


# Minor typing restriction, far from sound but better than nothing
Image = t.Union[numpy.ndarray]


def scale(image: Image, factor: float = 1) -> Image:
    """Scales an image by the given factor.

    Scales in both axes to preserve aspect ratio.
    """
    return cv2.resize(image, (0, 0), fx=factor, fy=factor, interpolation=cv2.INTER_AREA)


# https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_image_display/py_image_display.html


class ImageProcessor:
    """Abstract class for objects capable of transforming an image."""

    def process_frame(self, source: Image) -> t.Tuple[Image, t.Any]:
        """Performs no processing, base method."""
        return (source, None)


@dataclasses.dataclass()
class ChessboardFinder(ImageProcessor):
    """Looks for an processes a chessboard."""

    points_width: int
    points_height: int

    def process_frame(
        self, source: Image
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

    def process_frame(
        self, source: Image
    ) -> t.Tuple[Image, t.Sequence[t.Tuple[int, int]]]:
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

        # Pixel (corrected) to inches:
        # Sticky pad size:
        # 1 & 15/16 Inches = 1.9375 in
        # by 1 & 15/32 Inches = 1.46875 in
        # 233 by 168 pixels (approximate)
        # Ratio: 120.258 and 114.382 (not bad, not good)
        pixels_per_inch = 1  # TODO approximate measure, should also look at arcuro?

        def corrected(image: Image) -> Image:
            """Correct distortion of the image."""
            # roi: region of interest
            newCamMatrix, roi = cv2.getOptimalNewCameraMatrix(
                self.cam_matrix,
                self.dist_coeffs,
                imageSize=(image.shape[0], image.shape[1]),
                alpha=1,
                newImgSize=(image.shape[0], image.shape[1]),
            )
            # undistorted = cv2.undistort(
            #     image, self.cam_matrix, self.dist_coeffs, newCameraMatrix=newCamMatrix
            # )
            undistorted = cv2.undistort(image, self.cam_matrix, self.dist_coeffs)
            # x, y, width, height = roi
            # print(roi)
            # return undistorted[y:y+height, x:x+width]
            return undistorted

        # def cropped(image: Image) -> Image:
        #     """Crop step"""
        #     yMargin = 1  # 50
        #     leftMargin = 1  # 450
        #     rightMargin = 1  # 500
        #     return image[yMargin:-yMargin, leftMargin:-rightMargin].copy()

        def monoconvert(image: Image) -> Image:
            """Applies monoscale step"""
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        def blurred(image: Image) -> Image:
            """Applies blur step"""
            return cv2.blur(image, (5, 5))

        def thresholded(image: Image) -> Image:
            """Apply grayscale thresholding step.

            Expects single channel grayscale image.
            """
            _, thresh_output = cv2.threshold(image, 80, 255, cv2.THRESH_BINARY_INV)
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
        # cropped_image = cropped(corrected_image)
        mono = monoconvert(corrected_image)
        blur = blurred(mono)
        # blur = cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR)
        # filtered = hsv_filtered(blur)
        filtered = thresholded(blur)
        contours = contours_of(filtered)

        # output = cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)
        # output = cv2.cvtColor(blur, cv2.COLOR_GRAY2BGR)
        output = corrected_image
        # Parse contours
        MIN_SIZE = 10
        for contour in contours:
            # flatrect =cv2.boundingRect(contour)
            # https://docs.opencv.org/3.1.0/dd/d49/tutorial_py_contour_features.html
            rect = cv2.minAreaRect(contour)

            if rect[1][0] >= MIN_SIZE and rect[1][1] >= MIN_SIZE:
                # print(rect)
                box = numpy.int0(cv2.boxPoints(rect))

                blue = (255, 0, 0)
                green = (0, 255, 0)
                red = (0, 0, 255)
                highlight_color = blue
                highlight_thickness = 4
                text_color = green
                cv2.drawContours(output, [box], 0, highlight_color, highlight_thickness)
                cv2.putText(
                    output,
                    text="({:.2f}, {:.2f})".format(*[s / pixels_per_inch for s in rect[1]]),
                    org=tuple(map(int, rect[0])),
                    fontFace=cv2.FONT_HERSHEY_PLAIN,
                    fontScale=1.0,
                    color=text_color,
                    thickness=1,
                )

                sizes.append(rect)

        # print(sizes)

        # display = output
        # back = numpy.full(source.shape, 127, dtype=numpy.uint8)
        # back[:output.shape[0], :output.shape[1]] = output
        # print(source.shape, back.shape, source.dtype, back.dtype)
        display = scale(numpy.concatenate((source, output), axis=1), factor=1)

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
    last_request: int = 0

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
        logger.debug("Before initialize")
        cls.initialize()
        
        # logger.debug("Inside get_frame: %s", cls.frame)
        return cls.frame


    def __init__(self, processor: ImageProcessor) -> None:

        # Save processor ref for use in getting frames
        self.processor = processor

    def get_processed_frame(self) -> Image:
        """Returns the current frame of the processed video"""
        raw = type(self).get_frame()
        # logger.debug("Inside get_processed_frame: %s", raw)
        frame = self.processor.process_frame(raw)[0]
        logger.debug("Processed frame")
        return frame

    def get_jpg(self) -> bytes:
        """Returns the current frame, encoded as jpg"""
        return cv2.imencode(".jpg", self.get_processed_frame())[1].tobytes()


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
