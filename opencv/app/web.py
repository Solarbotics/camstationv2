"""Testing webapp"""

import logging
import typing as t

import flask

from . import camera
from . import calibrate
from . import config
from . import photo
from . import process
from . import scale

# Enable logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s")
)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

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

        pi_camera = process.get_camera()

        # inner generator
        def gen(cam: camera.Camera) -> t.Generator[bytes, None, None]:
            """Yields byte content of responses to reply with."""
            try:
                while True:
                    frame = cam.get_jpg(threshold=app.config.get("threshold", config.web.threshold))
                    yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            finally:
                pass
                # close_camera()

        # return a response streaming from the camera
        return flask.Response(
            gen(pi_camera), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


    @app.route("/bounds", methods=["GET", "POST"])
    def rect_dimensions() -> str:
        """Returns the current dimensions seen"""
        data = process.get_camera().get_processed_frame(
            threshold=app.config.get("threshold", config.web.threshold)
        )[1]
        return str(data[0])

    @app.route("/snap", methods=["POST"])
    def snap_corners() -> str:
        """Takes a snapshot and searches for chessboard corners."""
        # TODO magic numbers
        calibrate.save_snapshot(7, 5)
        return "Snapped"

    @app.route("/photos", methods=["POST"])
    def take_photos() -> str:
        """Take a photo from each remote camera."""
        photo.capture_image_set("photos")
        return "Photos taken"

    @app.route("/tare", methods=["POST"])
    def tare_scale() -> str:
        """Tare the scale."""
        with scale.managed_scale() as sc:
            sc.tare()
        return "Scale tared"

    @app.route("/weight", methods=["GET"])
    def get_weight() -> str:
        """Tare the scale."""
        with scale.managed_scale() as sc:
            weight = sc.read()
        return str(weight)

    @app.route("/config", methods=["POST"])
    def set_config() -> flask.Response:
        """Updates the config."""
        data = flask.request.json
        logger.info("Config: %s", data)
        app.config["threshold"] = int(data["threshold"])
        return flask.jsonify({"message": "Config updated"})

    @app.route("/activate", methods=["POST"])
    def activate() -> str:
        """Activate a round of the camera station."""
        return process.activate(threshold=app.config.get("threshold", config.web.threshold))

    # Teardown
    # app.teardown_appcontext(close_camera)

    return app


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
