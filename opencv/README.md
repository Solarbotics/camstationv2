# Camera Station

## Notes:

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
