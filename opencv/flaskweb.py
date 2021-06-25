"""Testing webapp"""

import logging
import typing as t

import flask
import numpy

import camera

# Enable logging
root_logger = logging.getLogger()
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s")
)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Load calibration matrices
camera_matrix = numpy.loadtxt("newCameraMatrix.txt", dtype="float", delimiter=",")
scale_matrix = numpy.loadtxt("cameraScaleMatrix.txt", dtype="float", delimiter=",")
camera_matrix *= scale_matrix
distortion_matrix = numpy.loadtxt("newCameraDistortion.txt", dtype="float", delimiter=",")

# TODO hmmm. would this scale well? production quality?
# Construct camera object
# TODO broken?
# pi_camera = camera.Camera(
#     processor=camera.ImageSizer(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
#     # processor=camera.ImageProcessor()
# )
def get_camera(app: flask.Flask) -> camera.Camera:
    """Get the camera."""
    if "camera" in flask.g:
        return flask.g.camera
    else:
        cam = camera.Camera(
            processor=camera.ImageSizer(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
            # processor=camera.ImageProcessor()
        )
        flask.g.camera = cam
        return cam

def close_camera(error: t.Optional[Exception] = None) -> None:
    """Close the camera."""
    cam = flask.g.pop("camera", None)
    if cam is not None:
        cam.close()
    


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
                    frame = cam.get_jpg()
                    yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            finally:
                close_camera()

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
        frame = pi_camera.frame
        if frame is not None:
            # TODO magic numbers
            processor = camera.ChessboardFinder(7, 5)
            _, result = processor.process_frame(frame)
            data, encoded = result

            print(data, encoded)

            with open("corners.npy", "wb+") as file:
                numpy.save(file, data)
            
            with open("example.jpg", "wb") as imFile:
                imFile.write(encoded)
            return "Snapped"
        else:
            return "No frame available"


    @app.route("/config", methods=["POST"])
    def set_config() -> str:
        """Updates the config."""
        print(flask.request.json)
        return "Success"

    # Teardown
    # app.teardown_appcontext(close_camera)

    return app


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
