"""Testing webapp"""

import logging
import typing as t

import flask

from . import camera
from . import calibrate
from . import config
from . import devices
from . import lights
from . import process

# Enable logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(config.logging.format))
root_logger.addHandler(handler)
root_logger.setLevel(config.logging.level)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Remove werkzeug handlers
werkzeug_logger = logging.getLogger("werkzeug")
# By prebuilding a list of handlers,
# we avoid iterating directly over the handler list
# that we are likely mutating
for _handler in list(werkzeug_logger.handlers):
    werkzeug_logger.removeHandler(_handler)


def no_json_error() -> flask.Response:
    """Response to be returned when JSON data was expected but not received."""
    response = flask.jsonify({"message": "No JSON received.", "valid": False})
    response.status_code = 415
    return response


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

        pi_camera = devices.get_camera()

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
        if data is not None:
            logger.info("Config: %s", data)
            app.config["threshold"] = int(data["threshold"])
            return flask.jsonify({"message": "Config updated"})
        else:
            return flask.jsonify({"message": "No JSON received."})

    @app.route("/lights", methods=["POST"])
    def set_lights() -> flask.Response:
        data = flask.request.json
        if data is not None:
            lights.Lights().ring().level = float(data["level"]) / 100
            return flask.jsonify({"message": "Lights updated."})
        else:
            return flask.jsonify({"message": "No JSON received."})

    @app.route("/bounds")
    def rect_dimensions() -> str:
        """Returns the current dimensions seen"""
        bounds = process.read_bounds(
            threshold=app.config.get("threshold", config.web.threshold)
        )
        return f"({bounds[0]:.2f}, {bounds[1]:.2f})"

    @app.route("/tare", methods=["POST"])
    def tare_scale() -> flask.Response:
        """Tare the scale."""
        weight = process.read_weight()
        app.config["tare"] = weight
        return flask.jsonify({"message": "Scale tared."})

    @app.route("/calibrate_depth", methods=["POST"])
    def calibrate_height() -> flask.Response:
        # Read current depth
        depth = process.read_height()
        app.config["base_depth"] = depth
        return flask.jsonify({"message": "Platform depth calibrated."})

    @app.route("/weight")
    def get_weight() -> str:
        """Read the scale."""
        return str(process.read_weight(tare=app.config.get("tare", 0)))

    @app.route("/height")
    def get_height() -> str:
        return str(process.read_height(base=app.config.get("base_depth", 0)))

    @app.route("/data")
    def get_data() -> flask.Response:
        """Retrive all the live data values."""
        weight = process.format_weight(
            process.read_weight(tare=app.config.get("tare", 0))
        )
        height = process.format_height(
            process.read_height(base=app.config.get("base_depth", 0))
        )
        bounds = process.format_bounds(
            process.read_bounds(
                threshold=app.config.get("threshold", config.web.threshold)
            )
        )
        message = {"weight": weight, "height": height, "bounds": bounds}
        return flask.jsonify(message)

    @app.route("/photos", methods=["POST"])
    def take_photos() -> flask.Response:
        """Take a photo from each remote camera."""
        data = flask.request.json
        if data is not None:
            query = data["query"]
            light_level = float(data["light_level"]) / 100
            encoded = process.collect_photos(query=query, light_level=light_level)
            return flask.jsonify(
                {"message": "success", "valid": True, "photos": encoded}
            )
        else:
            response = flask.jsonify({"message": "No JSON received.", "valid": False})
            response.status_code = 415
            return response

    @app.route("/grab_data", methods=["POST"])
    def grab_data() -> flask.Response:
        """Grabe live data values and save into data based on ILC."""
        data = flask.request.json
        if data is not None:
            logger.info(data)
            query = data["query"]
            data = process.collect_data(
                query=query,
                threshold=app.config.get("threshold", config.web.threshold),
                base_depth=app.config.get("base_depth", 0),
                tare=app.config.get("tare", 0),
                override_height=float(data["height_override"])
                if data["height_override"] is not None
                else None,
            )
            data["message"] = "success"
            data["valid"] = True
            return flask.jsonify(data)
        else:
            response = flask.jsonify({"message": "No JSON received.", "valid": False})
            response.status_code = 415
            return response

    @app.route("/setup", methods=["POST"])
    def setup() -> str:
        # Tare scale
        # Calibrate depth sensor
        weight = process.read_weight()
        depth = process.read_height()
        app.config["tare"] = weight
        app.config["base_depth"] = depth
        return "Setup complete."

    @app.route("/activate", methods=["POST"])
    def activate() -> flask.Response:
        """Activate a round of the camera station."""
        data = flask.request.json
        if not data:
            return flask.jsonify({"message": "Could not understand request."})
        logger.info("Data: %s", data)
        return flask.jsonify(
            process.activate(
                threshold=app.config.get("threshold", config.web.threshold),
                base_depth=app.config.get("base_depth", 0),
                tare=app.config.get("tare", 0),
                ilc=data["query"],
                height_override=float(data["height_override"])
                if data["height_override"] is not None
                else None,
                light_level=float(data["light_level"]) / 100,
            )
        )

    @app.route("/saved")
    def get_saved_data() -> t.Tuple[flask.Response, int]:
        """Return already collected data for an ILC."""
        try:
            ilc = flask.request.args["ilc"]
        except KeyError:
            return (
                flask.jsonify({"message": "Required `ilc` parameter is missing."}),
                404,
            )
        data = process.retrieve(ilc=ilc)
        if data is not None:
            return flask.jsonify({**data, "valid": True}), 200
        else:
            return flask.jsonify({"message": "No data.", "valid": False}), 200

    @app.route("/export", methods=["POST"])
    def export_data() -> flask.Response:
        """Export local data to an external location."""
        data = flask.request.json
        if data is None:
            return no_json_error()
        else:
            device = data["device"]
            process.export_data(device)
            return flask.jsonify({"message": "Success.", "valid": True})

    @app.route("/block_devices")
    def _get_block_devices() -> flask.Response:
        """Retrieve seen block devices."""
        return flask.jsonify({"devices": process.get_devices()})

    def _handle_device(method: t.Callable[[str], object]) -> flask.Response:
        """Perform a given action with a device."""
        data = flask.request.json
        if data is None:
            return no_json_error()
        else:
            device: str = data["device"]
            return flask.jsonify(method(device))

    @app.route("/mount_device", methods=["POST"])
    def _mount_device() -> flask.Response:
        """Mount the specified device."""
        return _handle_device(process.mount_device)

    @app.route("/unmount_device", methods=["POST"])
    def _unmount_device() -> flask.Response:
        """Unmount the specified device."""
        return _handle_device(process.unmount_device)

    return app
