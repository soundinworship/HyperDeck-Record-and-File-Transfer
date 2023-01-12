#!/usr/bin/env python3

import asyncio
import logging
#import argparse
import json
import sys

import WebUI
import HyperDeck

import webbrowser


local_data = []


async def main():
	ip = None
	local_download_folder = None

	with open('WebUI/Resources/local.json', 'r') as openfile:
		json_object = json.load(openfile)
		ip = json_object['hyperdeck-ip']
		local_download_folder = json_object['local-download-folder']

	hyperdeck = HyperDeck.HyperDeck(ip, 9993)
	await hyperdeck.connect()

	webui = WebUI.WebUI()

	await webui.start(hyperdeck, ip, local_download_folder)
	await hyperdeck.webUI(webui)

	webbrowser.open('http://127.0.0.1:8080/')
	
if __name__ == "__main__":
	logging.basicConfig(format='%(name)s %(levelname)s: %(message)s', level=logging.INFO)

	# Configure log level for the various modules.
	loggers = {
		'WebUI': logging.INFO,
		'HyperDeck': logging.INFO,
		'aiohttp': logging.ERROR,
	}
	for name, level in loggers.items():
		logger = logging.getLogger(name)
		logger.setLevel(level)

	# Parse command line arguments
	#parser = argparse.ArgumentParser()
	#parser.add_argument("-address", type=str, help="IP address of the HyperDeck to connect to", default=ip)
	#args = parser.parse_args()

	# Run the application with the user arguments
	loop = asyncio.new_event_loop()
	loop.run_until_complete(main())
	try:
		loop.run_forever()
		tasks = asyncio.all_tasks(loop)
		tasks = asyncio.gather(*tasks)
		loop.run_until_complete(tasks)
	except BaseException:
		pass
	finally:
		print('bye')
		loop.close()
		sys.exit()
