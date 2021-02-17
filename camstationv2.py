# This is a derivation of __main__py - for Cam-station project, by Kevin Loney for Solarbotics 2018-ish.
# Now that I've sorta played with rebuilding the same modules for a bit, I figured it made sense to
# rework what Kevin started to something to suit the new purposes.
# Feb 11 2021
#invoke usage with: $/home/dave/PycharmProjects/camstationv2/venv/bin/python /home/dave/PycharmProjects/camstationv2/__main__.py -d /tmp/camstation

import os
import sys
import json
import array
import signal
import asyncio
import hashlib
import logging
import argparse
import mimetypes
import configparser

import serial
import time
import re

import camscale

config = configparser.ConfigParser()
config.read('camstation.cfg')
comport = config.get('CAMSCALE', 'comport')
combaud = config.get('CAMSCALE', 'combaud')
imagepath = config.get('CAMFILEPATHS', 'imagepath')


# No idea. Gonna have to research
from concurrent.futures import ThreadPoolExecutor

# Set up logging...? No idea why the below modules are logged for failed load, and the ones at the top aren't
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s - %(message)s")
logging.getLogger('py.warnings').setLevel(logging.ERROR)
logging.captureWarnings(True)

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

# Todo {DMH} Get the RPi to control the relay for the lighting
# try:
# 	import RPi.GPIO as GPIO
# except ImportError:
# 	GPIO = None

# This allows applying a default to a function call
# https://stackoverflow.com/questions/15331726/how-does-functools-partial-do-what-it-does
from functools import partial

# Web tools
from tornado import escape, gen, httpclient, httpserver, httputil, ioloop, iostream, locks, web, websocket


# Application unknown presently
def resources_dir(*args):
	path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
	if args:
		path = os.path.join(path, *args)
	return path

# Command line arguments
#--dest points to the physical file location to store the imagery

# def get_cli_arguments():
# 	parser = argparse.ArgumentParser()
# 	parser.add_argument('-I', dest='interface', default='0.0.0.0')
# 	parser.add_argument('-p', dest='port', type=int, default=8080)
# 	parser.add_argument('-d', '--dest', required=True)
# 	return parser.parse_args()

# No idea presently
def enumerate_images(path, sku):
	if path is None:
		return

	search = os.path.join(path, sku)
	if not os.path.exists(search):
		return

	if not mimetypes.inited:
		mimetypes.init()

	for root, dirs, filenames in os.walk(search):
		for filename in filenames:
			filename = os.path.join(root, filename)
			type, encoding = mimetypes.guess_type(filename)

			if type.startswith('image/'):
				yield os.path.relpath(filename, start=path)

# Poll database for lookup of scanned SKU

dburl = config['CAMDATABASE']['url']
async def lookup_sku(sku, path=None):
	sku = sku.strip()
	if not sku:
		return

	result = {
		'sku': sku,
		'item': None,
	}

	logging.info('Lookup: %s', sku)

	client = httpclient.AsyncHTTPClient()
	try:
		url = httputil.url_concat(dburl, {'sku': sku})
		response = await client.fetch(url)
	except Exception as ex:
		# TODO: {KL} Log the exception
		logging.exception(ex)
	else:
		# TODO: {KL} Include any images already attached to the sku
		result['item'] = escape.json_decode(response.body)
		result['item']['images'] = list(enumerate_images(path, result['item']['active_bag']))

	await BroadcastHandler.event('lookup', result)

# No idea presently
def handler_hid(fd, events, path=None):
	content = fd.readline().strip()

	ioloop.IOLoop.current().add_callback(lookup_sku, content, path=path)

# No idea presently if implemented
def handler_shutdown(event):
	def shutdown_callback():
		logging.info('Shutdown signal received')
		event.set()

	def wrapper(signum, frame):
		ioloop.IOLoop.current().add_callback_from_signal(shutdown_callback)

	return wrapper

# Capture image subroutine.
# DAVE NO LIKE HASHING NAME STRUCTURE
def capture_image(camera, destination):
	try:
		# Setup and trigger the camera
		summary = camera.get_summary() # why this necessary? Cams are enumerated already
		digest = hashlib.md5(str(summary).encode('utf-8')).hexdigest()

		filename = os.path.join(destination, '%s.jpg' % digest)

		capture_path = camera.capture(gp.GP_CAPTURE_IMAGE)
		camera_file = camera.file_get(capture_path.folder, capture_path.name, gp.GP_FILE_TYPE_NORMAL)
		camera_file.save(filename)

		logging.info(filename)

	except Exception as ex:
		# TODO: {KL} Update status
		logging.exception(ex)

# Use GPhoto to get camera list, and create a camera index
def get_cameras():
	cameras = []

	port_info_list = gp.PortInfoList()
	port_info_list.load()

	for name, addr in gp.check_result(gp.gp_camera_autodetect()):
		idx = port_info_list.lookup_path(addr)

		camera = gp.Camera()
		camera.set_port_info(port_info_list[idx])
		camera.init()

		cameras.append(camera)

	return cameras


# ID if the scale is attached and functional
# def get_scale():
# 	device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
# 	if device is None:
# 		return None
#
# 	if device.is_kernel_driver_active(0):
# 		device.detach_kernel_driver(0)
#
# 	device.set_configuration()
#
# 	return device

# TARE the scale
async def tare_scale():
	scale = serial.Serial(port=comport, baudrate=combaud, timeout=4)
	scale.isOpen()
	print("Scale Port", comport, "opened")
	await asyncio.sleep(2)
	scale.write(b'x1x')  # Open menu; tare, close menu
	await asyncio.sleep(4)
	print("Tare complete")
	# logging.info('Taring scale')
	#
	# GPIO.setup(TARE_PIN, GPIO.OUT)
	#
	# GPIO.output(TARE_PIN, GPIO.LOW)
	# await asyncio.sleep(0.1)
	# GPIO.setup(TARE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Get mass from scale. Not sure where this is gleaned from, but wouldn't you know it that
# shortly after we did this project, Adafruit did something similar (and better, sigh!)
async def capture_weight():
	weight = None
	scale.write(b'r')
	scale.flushInput()
	scaleData = scale.readline().decode('ascii').split(',')
	# print("Scaledata:",scaleData)
	return scaleData[0]
	asyncio.sleep(0.1)
	endpoint = device[0][(0,0)][0]
	ioloop.IOLoop.current().add_callback(capture_weight)

	if weight is None:
		return

	await BroadcastHandler.weight(weight)

# Create data record...?
async def record(sku, metadata, path, cameras, pool):
	destination = os.path.join(path, sku)
	os.makedirs(destination, exist_ok=True)

	metapath = os.path.join(destination, 'metadata.json')
	with open(metapath, 'w') as file:
		json.dump(metadata, file)

	await BroadcastHandler.info('Starting capture')

	tasks = []
	cameras_connected = False
	for camera in cameras:
		cameras_connected = True

		task = asyncio.wrap_future(pool.submit(capture_image, camera, destination))
		tasks.append(task)

	if not cameras_connected:
		await BroadcastHandler.error('No cameras connected')
		return

	await asyncio.wait(tasks)

	await BroadcastHandler.info('Finished capture')

	ioloop.IOLoop.current().add_callback(lookup_sku, sku, path=path)

# No idea. Looks to be web-interface. Have to learn about classes
class BroadcastHandler(websocket.WebSocketHandler):
	connections = set()

	async def open(self):
		logging.info('WebSocket connected')
		self.connections.add(self)

	def on_close(self):
		self.connections.remove(self)
		logging.info('WebSocket disconnected')

	@classmethod
	async def error(cls, message):
		await cls.status('ERROR', message)

	@classmethod
	async def warn(cls, message):
		await cls.status('WARN', message)

	@classmethod
	async def info(cls, message):
		await cls.status('INFO', message)

	@classmethod
	async def status(cls, level, message):
		await cls.event('status', { 'level': level, 'message': message })

	@classmethod
	async def weight(cls, weight):
		await cls.event('weight', { 'weight': weight })

	@classmethod
	async def event(cls, type, data):
		await cls.broadcast({ 'type': type, 'data': data })

	@classmethod
	async def broadcast(cls, message):
		if len(BroadcastHandler.connections) > 0:
			await asyncio.wait([ws.write_message(message) for ws in BroadcastHandler.connections])

class RecordHandler(web.RequestHandler):
	def initialize(self, cameras, path, pool):
		self.cameras = cameras
		self.path = path
		self.pool = pool

	def put(self, sku):
		if gp is None or usb is None:
			self.set_status(501) # http code "Not Implemented"
		else:
			self.set_status(202) # (HTTP) 202 Accepted response status code indicates that the request has been accepted for processing
			metadata = escape.json_decode(self.request.body)
			ioloop.IOLoop.current().add_callback(record, sku, metadata, self.path, self.cameras, self.pool)

		self.finish()

class SearchHandler(web.RequestHandler):
	def initialize(self, path):
		self.path = path

	def post(self):
		sku = self.get_query_argument('sku')

		ioloop.IOLoop.current().add_callback(lookup_sku, sku, self.path)

		self.set_status(202)
		self.finish()

class ScaleHandler(web.RequestHandler):
	def initialize(self, device):
		self.device = device

	def post(self):
		if GPIO is None:
			self.set_status(501)
		else:
			self.set_status(202)
			ioloop.IOLoop.current().add_callback(tare_scale, self.device)

		self.finish()

class RestartHandler(web.RequestHandler):
	def initialize(self, event):
		self.event = event

	def post(self):
		self.event.set()

async def main():
	args = get_cli_arguments()

	# Setup shutdown handler
	shutdown = locks.Event()
	signal.signal(signal.SIGINT, handler_shutdown(shutdown))

	# Setup keyboard IO
	ioloop.IOLoop.current().add_handler(sys.stdin, partial(handler_hid, path=args.dest), ioloop.IOLoop.READ)

	scale = None
	cameras = []

	# TODO {DMH} - Change GPIO section to add LED control
	if GPIO:
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(TARE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	if gp:
		cameras = get_cameras()
	# TODO {DMH} - Replace scale routine
	if serial:
		scale = camscale.initscale()
		if scale:
			ioloop.IOLoop.current().add_callback(capture_weight, scale)

	with ThreadPoolExecutor(1) as pool:
		# Setup the web application
		application = web.Application([
			('/', web.RedirectHandler, {'url': '/index.html'}),
			('/ws', BroadcastHandler),
			('/api/search', SearchHandler, {'path': args.dest}),
			('/api/scale', ScaleHandler, {'device': scale}),
			('/api/restart', RestartHandler, {'event': shutdown}),
			('/api/record/(.+)', RecordHandler, {'path': args.dest, 'cameras': cameras, 'pool': pool}),
			('/captures/(.+)', web.StaticFileHandler, {'path': args.dest}),
			('/(.*)', web.StaticFileHandler, {'path': resources_dir('static')}),
		])

		http_server = httpserver.HTTPServer(application)
		http_server.listen(args.port, address=args.interface)

		logging.info('Server started on %s:%d', args.interface, args.port)

		await shutdown.wait()

	for camera in cameras:
		camera.exit()

if __name__ == '__main__':
	ioloop.IOLoop.current().run_sync(main)
