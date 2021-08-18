import gphoto2 as gp
import re


def get_cameras():
    cameras = []
    port_info_list = gp.PortInfoList()
    port_info_list.load()

    for name, addr in gp.check_result(gp.gp_camera_autodetect()):
        idx = port_info_list.lookup_path(addr)
        print("Lookup:",name,addr,idx)
        camera = gp.Camera()
        camera.set_port_info(port_info_list[idx])
        camera.init()
        cameras.append(camera)
    return cameras

def capture_image(camera, destination):
        # Setup and trigger the camera
        summary = camera.get_summary()
        # serial = camera.get_single_config('serialnumber')
        # print("Serial:",serial)

        camserial = camera.get_config()
        # print("serial:",camserial)
        camnum = re.search(r"(?<=Serial Number: ).*?(?=\s)", summary.text)[0]
        #digest = hashlib.md5(str(summary).encode('utf-8')).hexdigest()
        digest = '60D'
        print("SERIAL:",camnum)
        print(summary.text)


cameras = get_cameras()
for camera in cameras:
    capture_image(camera,'/home/dave/Pictures')