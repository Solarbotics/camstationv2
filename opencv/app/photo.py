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

def get_cameras() -> t.Sequence[gp.camera.Camera]:

    # Prepare list for cameras
    cameras = []
    port_info_list = gp.PortInfoList()
    port_info_list.load()

    for name, addr in gp.check_result(gp.gp_camera_autodetect()):
        idx = port_info_list.lookup_path(addr)
        print("[info]", name,addr,idx, sep=" <|> ")
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

def capture_image_set(folder: str) -> None:
    """Capture one photo from each camera."""
    # TODO make sure folder exists using path.mkdir or whatever
    for index, camera in enumerate(get_cameras()):
        capture_image(camera, folder+f"/{index}.jpg")

if __name__ == "__main__":
    all_cams = get_cameras()

    print(all_cams)
    # print(type(all_cams[0]))
    # print([entry for entry in dir(gp) if entry.lower().startswith("gp")])

    for index, cam in enumerate(all_cams):
        capture_image(cam, f"camImages/image{index}.jpg")

