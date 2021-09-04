# Let's try to get this thing to talk to some DSLRs
# Dave Hrynkiw, Alpha Feb 05 2021

import os
import re
import sys
import json
import array
import signal
import asyncio
import hashlib
import logging
import argparse
import mimetypes
import gphoto2 as gp

# Module load logging and error reporting
try:
    import gphoto2 as gp
except ImportError:
    logging.warn('Failed to import gphoto2')
    gp = None

try:
    import usb.core
    import usb.util
except ImportError:
    logging.warn('Failed to import usb')
    usb = None
    print('USB Set up')


# Capture image subroutine.
# DAVE NO LIKE HASHING NAME STRUCTURE
def capture_image(camera, destination):
    try:
        # Setup and trigger the camera
        summary = camera.get_summary()
        #context=gp.Context()

        camserial = camera.get_config()
        print("serial:",camserial)
        camnum = re.search(r"(?<=Current: ).*?(?=\s)", camserial)
        #digest = hashlib.md5(str(summary).encode('utf-8')).hexdigest()
        digest = '60D'
        print(summary.text)

        filename = os.path.join(destination, digest+'.jpg')
        print(filename)
        capture_path = camera.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = camera.file_get(capture_path.folder, capture_path.name, gp.GP_FILE_TYPE_NORMAL)
        camera_file.save(filename)

        logging.info(filename)

    except Exception as ex:
        # TODO: {KL} Update sta
        logging.exception(ex)


# Use GPhoto to get camera list, and create a camera index
def get_cameras():
    cameras = []
    port_info_list = gp.PortInfoList()
    port_info_list.load()

    for name, addr in gp.check_result(gp.gp_camera_autodetect()):
        idx = port_info_list.lookup_path(addr)
        print(name,addr,idx)
        camera = gp.Camera()
        camera.set_port_info(port_info_list[idx])
        camera.init()

        cameras.append(camera)
    return cameras


cameras = get_cameras()
for camera in cameras:
    capture_image(camera,'/home/dave/Pictures')

#clean up
# for camera in cameras:
#     camera.exit()