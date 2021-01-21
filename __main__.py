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

from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s - %(message)s")
logging.getLogger('py.warnings').setLevel(logging.ERROR)
logging.captureWarnings(True)

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

try:
	import RPi.GPIO as GPIO
except ImportError:
	GPIO = None

from functools import partial

from tornado import escape, gen, httpclient, httpserver, httputil, ioloop, iostream, locks, web, websocket

VENDOR_ID = 0x0922
PRODUCT_ID = 0x8003

TARE_PIN = 17

def resources_dir(*args):
	path = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
	if args:
		path = os.path.join(path, *args)
	return path

def get_cli_arguments():
	parser = argparse.ArgumentParser()

	parser.add_argument('-I', dest='interface', default='0.0.0.0')
	parser.add_argument('-p', dest='port', type=int, default=8080)
	parser.add_argument('-d', '--dest', required=True)

	return parser.parse_args()

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
		url = httputil.url_concat('http://192.168.2.8:9002/lookup.json', {'sku': sku})
		response = await client.fetch(url)
	except Exception as ex:
		# TODO: {KL} Log the exception
		logging.exception(ex)
	else:
		# TODO: {KL} Include any images already attached to the sku
		result['item'] = escape.json_decode(response.body)
		result['item']['images'] = list(enumerate_images(path, result['item']['active_bag']))

	await BroadcastHandler.event('lookup', result)

def handler_hid(fd, events, path=None):
	content = fd.readline().strip()

	ioloop.IOLoop.current().add_callback(lookup_sku, content, path=path)

def handler_shutdown(event):
	def shutdown_callback():
		logging.info('Shutdown signal received')
		event.set()

	def wrapper(signum, frame):
		ioloop.IOLoop.current().add_callback_from_signal(shutdown_callback)

	return wrapper

def capture_image(camera, destination):
	try:
		# Setup and trigger the camera
		summary = camera.get_summary()
		digest = hashlib.md5(str(summary).encode('utf-8')).hexdigest()

		filename = os.path.join(destination, '%s.jpg' % digest)

		capture_path = camera.capture(gp.GP_CAPTURE_IMAGE)
		camera_file = camera.file_get(capture_path.folder, capture_path.name, gp.GP_FILE_TYPE_NORMAL)
		camera_file.save(filename)

		logging.info(filename)

	except Exception as ex:
		# TODO: {KL} Update status
		logging.exception(ex)

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

def get_scale():
	device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
	if device is None:
		return None

	if device.is_kernel_driver_active(0):
		device.detach_kernel_driver(0)

	device.set_configuration()

	return device

async def tare_scale(device):
	logging.info('Taring scale')

	GPIO.setup(TARE_PIN, GPIO.OUT)

	GPIO.output(TARE_PIN, GPIO.LOW)
	await asyncio.sleep(0.1)

	GPIO.setup(TARE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

async def capture_weight(device):
	DATA_MODE_GRAMS = 2
	DATA_MODE_OUNCES = 11

	weight = None
	endpoint = device[0][(0,0)][0]

	scaling_factors = {
		255: 0.1,
		254: 0.01,
	}

	try:
		data = device.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize)

		raw_weight = data[4] + data[5] * 256
		if data[2] == DATA_MODE_OUNCES:
			scaling_factor = scaling_factors.get(data[3], None)
			if scaling_factor is None:
				raise Exception('Unexpected weight scaling factor [%d]', data[3])

			weight = 28.3495 * scaling_factor * raw_weight
		elif data[2] == DATA_MODE_GRAMS:
			weight = raw_weight

		if not weight is None and data[1] == 5:
			weight *= -1

	except Exception as ex:
		logging.exception(ex)

	ioloop.IOLoop.current().add_callback(capture_weight, device)

	if weight is None:
		return

	await BroadcastHandler.weight(weight)

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
			self.set_status(501)
		else:
			self.set_status(202)
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

	if GPIO:
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(TARE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	if gp:
		cameras = get_cameras()

	if usb:
		scale = get_scale()
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
