"""Take photos using remote cameras using gphoto2."""

import typing as t

# note: using gphoto2 requires the user to be in the plugdev group (or root)
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


def get_cameras() -> t.Sequence[gp.camera.Camera]:

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


def capture_image(camera, destination: str) -> None:
    """Capture and download an image from the given camera."""
    # trigger camera?
    summary = camera.get_summary()

    path_on_camera = camera.capture(gp.GP_CAPTURE_IMAGE)
    camera_file = camera.file_get(
        path_on_camera.folder, path_on_camera.name, gp.GP_FILE_TYPE_NORMAL
    )
    camera_file.save(destination)


def capture_image_set(folder: str = "photos") -> t.Iterable[str]:
    """Capture one photo from each camera.

    Returns iterable of file names that were saved to.
    """
    file_names = []
    for index, camera in enumerate(get_cameras()):
        # Info of the camera path, i.e. the port its connected to
        camera_path_info = camera.get_port_info().get_path()
        # print(camera_path_info)
        # Transform into a set name (e.g. 'overhead', 'side', etc)
        name = config.photo.names.get(camera_path_info, "unknown")
        # Construct filename as a string to give to gphoto
        save_path = files.data_name(
            name=name, folder=folder, extension="jpg", timestamp=True
        )
        file_names.append(save_path)

        capture_image(camera, save_path)

    # print(file_names)
    # return ["photos/0.jpg"]
    return file_names


if __name__ == "__main__":
    capture_image_set()
