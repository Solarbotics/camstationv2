"""Testing webapp"""

import logging
import typing as t

import flask

from . import camera
from . import calibrate
from . import config
from . import lights
from . import measure
from . import photo
from . import process
from . import scale

# Enable logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(config.logging.format))
root_logger.addHandler(handler)
root_logger.setLevel(config.logging.level)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

werkzeug_logger = logging.getLogger("werkzeug")
# By prebuilding a list of handlers,
# we avoid iterating directly over the handler list
# that we are likely mutating
for _handler in list(werkzeug_logger.handlers):
    werkzeug_logger.removeHandler(_handler)

# logging.getLogger("app.camera").setLevel(logging.INFO)


def close_camera(error: t.Optional[Exception] = None) -> None:
    """Close the camera."""
    # cam = flask.g.pop("camera", None)
    # if cam is not None:
    #     cam.close()


def create_app() -> flask.Flask:
    """Create and setup the Flask application."""

    app = flask.Flask(__name__, static_url_path="")

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
                    frame = cam.get_jpg(
                        threshold=app.config.get("threshold", config.web.threshold)
                    )
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
        bounds = tuple(f"{val:.2f}" for val in (data[0] if data else (0, 0)))
        return f"({bounds[0]}, {bounds[1]})"

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
        """Read the scale."""
        with scale.managed_scale() as sc:
            weight = sc.read()
        return str(weight)

    @app.route("/config", methods=["POST"])
    def set_config() -> flask.Response:
        """Updates the config."""
        data = flask.request.json
        if data is not None:
            logger.info("Config: %s", data)
            app.config["threshold"] = int(data["threshold"])
            return flask.jsonify({"message": "Config updated"})
        else:
            return flask.jsonify({"message": "No JSON received."})

    @app.route("/lights", methods=["POST"])
    def set_lights() -> flask.Response:
        data = flask.request.json
        if data:
            lights.Lights().ring().level = float(data["level"]) / 100
            return flask.jsonify({"message": "Lights updated."})
        else:
            return flask.jsonify({"message": "No JSON received."})

    @app.route("/calibrate_depth", methods=["POST"])
    def calibrate_height() -> flask.Response:
        # Read current depth
        with measure.sensor() as sensor:
            depth = sensor.read()
        app.config["base_depth"] = depth
        return flask.jsonify({"message": "Platform depth calibrated."})

    @app.route("/height")
    def get_height() -> str:
        with measure.sensor() as sensor:
            return str(sensor.obtain(base=app.config.get("base_depth", 0)))

    @app.route("/setup", methods=["POST"])
    def setup() -> str:
        # Tare scale
        # Calibrate depth sensor
        with scale.managed_scale() as sc:
            sc.tare()
        with measure.sensor() as sensor:
            depth = sensor.read()
        app.config["base_depth"] = depth
        return "Setup complete."

    @app.route("/activate", methods=["POST"])
    def activate() -> flask.Response:
        """Activate a round of the camera station."""
        return flask.jsonify(
            process.activate(
                threshold=app.config.get("threshold", config.web.threshold),
                base_depth=app.config.get("base_depth", 0),
            )
        )

    # Teardown
    # app.teardown_appcontext(close_camera)

    return app
