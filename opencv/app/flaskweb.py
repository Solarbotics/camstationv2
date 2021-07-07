"""Testing webapp"""

import logging
import typing as t

import flask
import numpy

from . import camera
from . import calibrate

# Enable logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s")
)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Load calibration matrices
camera_matrix = numpy.loadtxt("cameraMatrix.txt", dtype="float", delimiter=",")
scale_matrix = numpy.loadtxt("cameraScaleMatrix.txt", dtype="float", delimiter=",")
camera_matrix *= scale_matrix
distortion_matrix = numpy.loadtxt("cameraDistortion.txt", dtype="float", delimiter=",")

# TODO hmmm. would this scale well? production quality?
# Construct camera object
# TODO broken?
# pi_camera = camera.Camera(
#     processor=camera.ImageSizer(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
#     # processor=camera.ImageProcessor()
# )
def get_camera(app: flask.Flask) -> camera.Camera:
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
        processor=camera.ImageSizer(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
        # processor=camera.ImageProcessor()
    )

def close_camera(error: t.Optional[Exception] = None) -> None:
    """Close the camera."""
    # cam = flask.g.pop("camera", None)
    # if cam is not None:
    #     cam.close()
    
DEFAULT_THRESHOLD = 80

def create_app() -> flask.Flask:
    """Create and setup the Flask application."""

    app = flask.Flask(__name__, static_url_path="/static", static_folder="static")

    @app.route("/")
    def index() -> str:
        """Index page"""
        return flask.render_template("index.html")


    # https://blog.miguelgrinberg.com/post/video-streaming-with-flask
    @app.route("/camera")
    def video_feed() -> flask.Response:
        """Returns the modified camera stream."""

        pi_camera = get_camera(app)

        # inner generator
        def gen(cam: camera.Camera) -> t.Generator[bytes, None, None]:
            """Yields byte content of responses to reply with."""
            try:
                while True:
                    frame = cam.get_jpg(threshold=app.config.get("threshold", DEFAULT_THRESHOLD))
                    yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            finally:
                pass
                # close_camera()

        # return a response streaming from the camera
        return flask.Response(
            gen(pi_camera), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


    @app.route("/dims")
    def rect_dimensions() -> str:
        """Returns the current dimensions seen"""


    @app.route("/snap", methods=["POST"])
    def snap_corners() -> str:
        """Takes a snapshot and searches for chessboard corners."""
        # TODO magic numbers
        calibrate.save_snapshot(7, 5)
        return "Snapped"


    @app.route("/config", methods=["POST"])
    def set_config() -> flask.Response:
        """Updates the config."""
        data = flask.request.json
        logger.info("Config: %s", data)
        app.config["threshold"] = int(data["threshold"])
        return flask.jsonify({"message": "Config updated"})

    # Teardown
    # app.teardown_appcontext(close_camera)

    return app


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
