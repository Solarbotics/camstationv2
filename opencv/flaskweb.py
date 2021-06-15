"""Testing webapp"""

import typing as t

import flask
import numpy

import camera

# flask app
app = flask.Flask(__name__, static_url_path="/static", static_folder="static")

camera_matrix = numpy.loadtxt("cameraMatrix.txt", dtype="float", delimiter=",")
distortion_matrix = numpy.loadtxt("cameraDistortion.txt", dtype="float", delimiter=",")

@app.route("/")
def index() -> str:
    """Index page"""
    return flask.render_template("index.html")


# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
@app.route("/camera")
def video_feed() -> flask.Response:
    """Returns the modified camera stream."""

    # Construct camera object
    pi_camera = camera.Camera(
        processor=camera.ImageProcessor(cam_matrix=camera_matrix, dist_coeffs=distortion_matrix)
    )

    # inner generator
    def gen(cam: camera.Camera) -> t.Generator[bytes, None, None]:
        """Yields byte content of responses to reply with."""
        try:
            while True:
                frame = cam.get_jpg()
                yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        finally:
            pi_camera.close()

    # return a response streaming from the camera
    return flask.Response(
        gen(pi_camera), mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/dims")
def rect_dimensions() -> str:
    """Returns the current dimensions seen"""

@app.route("/config", methods=["POST"])
def set_config() -> str:
    """Updates the config."""
    print(flask.request.form)
    return "Success"

# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
