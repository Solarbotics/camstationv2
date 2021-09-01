# Camera Station

This is the next iteration of the mobile Camstation that we worked with [Kevin Loney](https://github.com/solarboticsltd/Internal-Tools/blob/master/cam_station/).

## Goals

Procedure:
 1. Roll down a store's isle
 2. Take a product and
	 1. Scan it (barcode / etc)
	 2. Confirm its database details (polling RMS / QB Databases) and pull any historic data
	 3. Photograph it (using 2 or 3 cameras using gphoto library)
	 4. Weigh it (using Sparkfun Scale Module)
	 5. Dimension it by
		1. Using underside camera picture of shadow-cast to get X by Y
		2. Use overhead Time-of-Flight sensor to read any change in plane to get Z-offset
 3. Save the data to a database for inclusion to the Solarbotics.com website.

Documented on the Solarbotics' internal wiki at:
 - http://192.168.2.8/index.php/camstation-v2-development-list/ and 
 - http://192.168.2.8/index.php/realsense-camera-depth-measurement-for-camstation/camstation-v2-hardware/

## Usage
 - The Raspberry Pi controlling the camera station
 can be found at the address `camerastation` (or `192.168.2.169` as of writing).
 - Activate venv (e.g. `. camvenv/bin/venv` from root repository directory),
 - Start Flask (i.e. `flask run -h <address>`) (defaults to localhost address),
 which starts the app named within `.env`,
 - Buttons are labelled with what they get, `Activate` should run everything.

## Structure

Parts:
 - Raspberry Pi Camera Module (`opencv` box detection for width and length)
 - VL53L0X distance sensor (height detection)
 - DSLR Cameras (product photos)
 - Weight scale (product weight)
 - Lights (illuminating product and shadowcast)

## Behaviour

Activation:
 - Get bounds from undercamera using opencv shadow-based box detection
 - Read scale
 - Read height distance sensor
 - Turn on ring lights underneath
 - Take photos from connected cameras
 - Turn of ring lights
 - Save data into files and return data to website

Keybinds:
 - `s` selects query search box

## Data

Distances are always reported in cm, and weight in kg.

## Notes

Groups required:
 - `plugdev` for usb photo camera
 - `dialout` (`tty` may also be required) for scale
 - `video` for something (picamera likely)
 - `gpio` for gpio access (for lights)
 - `i2c` for i2c access (for ToF sensor)

System Dependencies:
 - `pmount` (get from e.g. `apt-get`)

Photo:
 - Prone to giving random errors.
   Restarting the camera(s) and running `gphoto2 --reset` 
   may alleviate some of these.
