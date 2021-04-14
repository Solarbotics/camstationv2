#   Let's try to get a function written that talks to the Active Database
#    DMH - April 7 2021
# ref:  lookup_sku - Polls database for required SKU/Item data
# in the __main__ function

# Poll database for lookup of scanned SKU
import logging
from tornado import httpclient, escape
from camstationv2 import BroadcastHandler


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
		from tornado import httputil
		url = httputil.url_concat('http://192.168.2.8:9002/lookup.json', {'sku': sku})
		response = await client.fetch(url)
	except Exception as ex:
		# TODO: {KL} Log the exception
		logging.exception(ex)
	else:
		# TODO: {KL} Include any images already attached to the sku
		result['item'] = escape.json_decode(response.body)
		print(result['item'])
		# result['item']['images'] = list(enumerate_images(path, result['item']['active_bag']))

	await BroadcastHandler.event('lookup', result)

print("Here's da thing:", lookup_sku('404040'))