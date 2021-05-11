"""Testing webapp"""

import typing as t

import flask

import camera

# flask app
app = flask.Flask(__name__)


@app.route("/")
def index() -> str:
    """Index page"""
    return flask.render_template("index.html")


# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
@app.route("/camera")
def video_feed() -> flask.Response:
    """Returns the modified camera stream."""

    # inner generator
    def gen(cam: camera.Camera) -> t.Generator[bytes, None, None]:
        """Yields byte content of responses to reply with."""
        while True:
            frame = cam.get_jpg()
            yield b"--frame\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"

    # return a response streaming from the camera
    return flask.Response(
        gen(camera.Camera()), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# https://www.pyimagesearch.com/2019/09/02/opencv-stream-video-to-web-browser-html-page/
# https://blog.miguelgrinberg.com/post/video-streaming-with-flask
# https://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/
