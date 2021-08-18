# Camera Station

## Usage
 - The Raspberry Pi controlling the camera station
 can be found at the address `camerastation` (or `192.168.2.165` as of writing).
 - Activate venv (e.g. `. camvenv/bin/venv` from `opencv` directory)
 - Start Flask (i.e. `flask run -h <address>`) (defaults to localhost address)
 - Buttons are labelled with what they get, `Activate` should run everything

## Structure

Parts:
 - Raspberry Pi Camera Module (`opencv` box detection for width and length)
 - VL53L0X distance sensor (height detection)
 - DSLR Cameras (product photos)
 - Weight scale (product weight)
 - Lights (illuminating product and shadowcast)

## Behaviour

Activation:
 - Turn on lights
 - Get bounds from undercamera using opencv shadow-based box detection
 - Turn off lights
 - Read scale
 - Read height distance sensor (TODO: use calibration to calculate height, not depth)
 - Take photos from connected cameras
 - Save data into files and return data to website

## Notes

Groups required:
 - `plugdev` for usb photo camera
 - `dialout` (`tty` may also be required) for scale
 - `video` for something (picamera likely)
 - `gpio` for gpio access (for lights)
 - `i2c` for i2c access (for ToF sensor)

Photo:
 - Prone to giving random errors.
   Restarting the camera(s) and running `gphoto2 --reset` 
   may alleviate some of these.
