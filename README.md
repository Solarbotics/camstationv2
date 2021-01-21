# camstationv2
Mobile product documentation Camera station

This is the next iteration of the mobile Camstation that we worked with [Kevin Loney](https://github.com/solarboticsltd/Internal-Tools/blob/master/cam_station/) to create something that we could:

 1. Roll down a store's isle
 2. Take a product and
	 1. Scan it (barcode / etc)
	 2. Confirm its database details (polling RMS / QB Databases)
	 3. Photograph it (using 2 or 3 cameras)
	 4. Weigh it (using Sparkfun Scale Module)
	 5. Dimension it by
		1. Using underside camera picture of shadow-cast to get X by Y
		2. Use overhead Time-of-Flight sensor to read any change in plane to get Z-offset
 3. Save the data to a database for inclusion to the Solarbotics.com website.
 
 This is well documented on the Solarbotics' internal wiki at 
 - http://192.168.2.8/index.php/camstation-v2-development-list/ and 
 - http://192.168.2.8/index.php/realsense-camera-depth-measurement-for-camstation/camstation-v2-hardware/

