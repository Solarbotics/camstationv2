"""Take photos using remote cameras using gphoto2."""

import argparse
import base64
import dataclasses
import datetime
import logging
import typing as t

# note: using gphoto2 requires the user to be in the plugdev group (or root)
import cv2
import gphoto2 as gp

# camera = gp.Camera()
# print(gp.check_result(gp.gp_camera_autodetect()))
# camera.init()
# print(dir(camera))
# print(str(camera.get_summary()))

# port_info_list = gp.PortInfoList()
# port_info_list.load()
# print(list(port_info_list))

from . import config
from . import files

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


T = t.TypeVar("T")


@dataclasses.dataclass()
class IterableManager(t.Generic[T]):
    """Wraps an iterable in a context manager.

    Returns the iterable on entry,
    and calls the provided cleanup function
    on each item of the iterable on exit.

    Note that if the iterable is single-use,
    objects may not be cleaned up correctly.
    """

    items: t.Iterable[T]
    cleanup: t.Callable[[T], object] = lambda x: None

    def __enter__(self) -> t.Iterable[T]:
        """Provide wrapped iterable in context."""
        return self.items

    def __exit__(self, *exc_info) -> None:
        """Cleanup items in wrapped iterable."""
        for item in self.items:
            self.cleanup(item)


def get_cameras() -> t.Sequence[gp.camera.Camera]:
    """Open all detected cameras.

    Caller is responsible for closing each camera,
    although they will also usually be closed on memory cleanup.
    """

    # Prepare list for cameras
    cameras = []
    port_info_list = gp.PortInfoList()
    port_info_list.load()

    for name, addr in gp.check_result(gp.gp_camera_autodetect()):
        idx = port_info_list.lookup_path(addr)
        # print("[info]", name, addr, idx, sep=" <|> ")
        camera = gp.Camera()
        camera.set_port_info(port_info_list[idx])
        # print(port_info_list[idx].get_name())
        camera.init()

        cameras.append(camera)
    return cameras


def close_camera(camera) -> None:
    """Cleanup the provided camera."""
    logger.info("Closing camera %s", camera)
    camera.exit()


def config_value(camera, key: str) -> str:
    """Retrieve the value of the requested config key of the provided camera.

    Example keys:
    'serialnumber',
    'cameramodel',
    """
    return gp.check_result(
        gp.gp_widget_get_child_by_name(camera.get_config(), key)
    ).get_value()


def cameras_info() -> t.Sequence[t.Sequence[str]]:
    """Open and collect information on connected cameras.

    Closes the cameras automatically.
    """
    with IterableManager(get_cameras(), close_camera) as cameras:
        return [
            (config_value(camera, "cameramodel"), config_value(camera, "serialnumber"))
            for camera in cameras
        ]


def capture_image(camera, destination: str) -> None:
    """Capture and download an image from the given camera."""
    # trigger camera?
    summary = camera.get_summary()

    path_on_camera = camera.capture(gp.GP_CAPTURE_IMAGE)
    camera_file = camera.file_get(
        path_on_camera.folder, path_on_camera.name, gp.GP_FILE_TYPE_NORMAL
    )
    camera_file.save(destination)


def capture_image_set(
    folder: str = "photos", timestamp: t.Optional[datetime.datetime] = None
) -> t.Iterable[str]:
    """Capture one photo from each camera.

    Returns iterable of file names that were saved to.
    """
    file_names = []
    with IterableManager(get_cameras(), close_camera) as cameras:
        for index, camera in enumerate(cameras):
            # Serial number of the camera for keying
            serialnumber = config_value(camera, "serialnumber")
            # Transform into a set name (e.g. 'overhead', 'side', etc)
            name = config.photo.names.get(serialnumber, "unknown")
            # Construct filename as a string to give to gphoto
            save_path = files.data_name(
                name=name,
                folder=folder,
                extension="jpg",
                use_timestamp=True,
                timestamp=timestamp,
            )
            file_names.append(save_path)

            capture_image(camera, save_path)

    logger.info("Photos: %s", file_names)
    # return ["photos/0.jpg"]
    return file_names


def encode_image(path: str) -> str:
    """Encode an image from a file path into unicode base64.

    Also scales the image to display and transport reasonably."""
    HEIGHT = 300
    # Read and resize photo
    loaded_photo = cv2.imread(path)
    loaded_photo = cv2.resize(
        loaded_photo,
        # dsize is (width, height), but .shape is (rows, columns)
        dsize=(int(loaded_photo.shape[1] / loaded_photo.shape[0] * HEIGHT), HEIGHT),
        interpolation=cv2.INTER_AREA,
    )
    # Encode into jpg and then b64 of that jpg
    # Allows easy sending over http and then loading into html img tag
    jpg_bytes = cv2.imencode(".jpg", loaded_photo)[1].tobytes()
    b64_encoding = base64.b64encode(jpg_bytes).decode("ascii")
    return b64_encoding


def cmd(arguments: t.Optional[t.Sequence[str]] = None) -> None:
    """Run argparse and command-line functionality."""
    parser = argparse.ArgumentParser(
        description="Interact with connected photo cameras."
    )
    parser.add_argument(
        "mode", choices=("capture", "detect"), default="detect", help="Mode to run."
    )

    args = parser.parse_args(arguments)

    if args.mode == "capture":
        paths = capture_image_set()
        print(f"Images captured: {paths}")
    elif args.mode == "detect":
        info = cameras_info()
        for piece in info:
            print(f"Info: {piece}")


if __name__ == "__main__":
    cmd()
