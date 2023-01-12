import asyncio
import logging
import json
import ftplib
import os
from tkinter import ttk
import tkinter as tk
import webbrowser
import sys
import datetime
import json
from datetime import datetime as dt

try:
	import aiohttp
	from aiohttp import web
except ImportError:
	print("The aiohttp library was not found. Please install it via `pip install aiohttp` and try again.")
	import sys
	sys.exit(1)




class WebUI:
	logger = logging.getLogger(__name__)

	def __init__(self, port=None, loop=None):
		self.port = port or 8080

		self._loop = loop or asyncio.get_event_loop()
		self._hyperdeck = None
		self._websocket = None
		self._ip = None
		self._local_download_folder = None
		self.server = None
		self.app = None

	async def start(self, hyperdeck, ip, local_download_folder):
		self._hyperdeck = hyperdeck
		self._ip = ip
		self._local_download_folder = local_download_folder

		# Add routes for the static front-end HTML file, the websocket, and the resources directory.
		app = web.Application()
		app.router.add_get('/', self._http_request_get_frontend_html)
		app.router.add_get('/ws', self._http_request_get_websocket)
		app.router.add_static('/resources/', path=str('./WebUI/Resources/'))

		self.logger.info("Starting web server on localhost:{}".format(self.port))
		self.server = await self._loop.create_server(app.make_handler(), "localhost", self.port)
		self.app = app

	async def _http_request_get_frontend_html(self, request):
		return web.FileResponse(path=str('WebUI/WebUI.html'))

	async def _http_request_get_websocket(self, request):
		ws = web.WebSocketResponse()
		await ws.prepare(request)

		self._websocket = ws
		await self._hyperdeck.set_callback(self._hyperdeck_event)

		async for msg in ws:
			if msg.type == aiohttp.WSMsgType.TEXT:
				request = json.JSONDecoder().decode(msg.data)
				self.logger.debug("Front-end request: {}".format(request))

				try:
					await self._websocket_request_handler(request)
				except Exception as e:
					logging.error(e)
			elif msg.type == aiohttp.WSMsgType.ERROR:
				logging.error('Websocket connection closed with exception {}'.format(ws.exception()))

		return ws
	
	async def read_settings(self, reason):
		with open('WebUI/Resources/settings.json', 'r') as openfile:
				json_object = json.load(openfile)
		message = {
			'response': 'read_settings',
			'params': {
				'reason': reason,
				'auto-record': json_object['auto-record'],
				'auto-download': json_object['auto-download']
			}
		}
		await self._send_websocket_message(message)

	async def loading(self,status):
		await asyncio.sleep(0) #strangely enough, loading doesn't work without this
		message = {
			'response': 'loading',
			'params': {
				'status': status
			}
		}
		await self._send_websocket_message(message)

	
	async def _websocket_request_handler(self, request):
		await self.loading(True)
		command = request.get('command')
		params = request.get('params', dict())

		# Process the various commands the front-end can send via the websocket.
		if command == "refresh":
			await self._hyperdeck_event('clips')
			await self._hyperdeck_event('status')
			slots = []
			for s in ['1','2']:
				response = await self._hyperdeck.slotInfo(s)
				if response['lines'][2:][0] == 'status: mounted':
					slots.append(s)
			message = {
				'response': 'sd_slots',
				'params': {
					'slots': slots
				}
			}
			await self._send_websocket_message(message)
		elif command == "get_settings":
			await self.read_settings("startup")
		elif command == "set_settings":
			settings ={
				"auto-record": params.get('auto-record'),
				"auto-download": params.get('auto-download')
				}
			json_object = json.dumps(settings, indent=4)
			with open("WebUI/Resources/settings.json", "w") as outfile:
				outfile.write(json_object)
			message = {
				'response': 'settings_saved',
				'params': {
					'status': 'Complete'
				}
			}
			await self._send_websocket_message(message)
		elif command == "record":
			name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
			await self._hyperdeck.record(name)
			message = {
				'response': 'alert',
				'params': {
					'status': 'Recording',
					'action': 'start'
				}
			}
			await self._send_websocket_message(message)
		elif command == "play":
			single = params.get('single', False)
			loop = params.get('loop', False)
			speed = params.get('speed', 1.0)

			await self._hyperdeck.play(single=single, loop=loop, speed=speed)
		elif command == "stop":
			await self._hyperdeck.stop()
			message = {
				'response': 'alert',
				'params': {
					'status': 'Recording Complete',
					'action': 'close'
				}
			}
			await self._send_websocket_message(message)
			message = {
				'response': 'clip_refresh',
				'params': {
					'reasom': 'Show new recording',
				}
			}
			await self._send_websocket_message(message)
			await self.read_settings("download")
		elif command == 'download_latest_clip':
			ftp = ftplib.FTP(self._ip)
			ftp.login()

			# in root to start
			fileList = []
			slots = []
			for item in ftp.nlst():
					slots.append(item)

			for s in slots:
				ftp.cwd('/') #start in root
				ftp.cwd('/'+s+'/') #go to each folder/slot in the machine
				files = ftp.nlst()
				for f in files:
					if f[-4:] == '.mp4':
						fileList.append(f)
				ftp.cwd('/') #end in root
			ftp.quit()
			sortedFileList = sorted(fileList)
			message = {
				'response': 'download_clip',
				'params': {
					'clip': sortedFileList[len(sortedFileList)-1], #last file in sorted list
				}
				}
			await self._send_websocket_message(message)
		elif command == "state_refresh":
			await self._hyperdeck.update_status()
		elif command == "view":
			await self._hyperdeck.preview()
		elif command == "config":
			response = await self._hyperdeck.configQuery()
			send_info = ""
			if response['code'] == 211:
				info_needed = response['lines'][2:]
				for info in info_needed:
					if 'audio' in info or 'video' in info:
						send_info += info + '<br>'
				message = {
					'response': 'alert',
					'params': {
						'status': send_info,
						'action': 'close'
					}
				}
				await self._send_websocket_message(message)
		elif command == "slot select":
			slot = params.get("id")
			response = await self._hyperdeck.slotSelect(slot)
			if response['code'] == 200:
				message = {
					'response': 'slot_select',
					'params': {
						'slot': slot
					}
				}
				await self._send_websocket_message(message)
				slot_info = await self._hyperdeck.slotInfo(slot)
				send_info = ""
				if slot_info['code'] == 202:
					slot_needed = slot_info['lines'][2:]
					for info in slot_needed:
						send_info += info + '<br>'
					message = {
						'response': 'alert',
						'params': {
							'status': send_info,
							'action': 'close'
						}
					}
					await self._send_websocket_message(message)

		elif command == "format":
			f = params.get("f")
			response = await self._hyperdeck.format("prepare",f)	
			if response['code'] == 216:
				message = {
					'response': 'format_confirm',
					'params': {
						'token': response['lines'][1]
					}
				}
				await self._send_websocket_message(message)
			else:
				message = {
					'response': 'alert',
					'params': {
						'status': 'Selected Disk',
						'action': 'close'
					}
				}
				await self._send_websocket_message(message)
		elif command == "format_confirm":
			token = params.get("token")
			response = await self._hyperdeck.format("confirm",token)
			if response['code'] == 200:
				message = {
					'response': 'alert',
					'params': {
						'status': 'Format Complete',
						'action': 'close'
					}
				}
				await self._send_websocket_message(message)
			else:
				message = {
					'response': 'alert',
					'params': {
						'status': 'An error occurred',
						'action': 'close'
					}
				}
				await self._send_websocket_message(message)
		elif command == "browser_close":
			print('browser closed')
			await self._hyperdeck.shutdown()
			await self._websocket.close()
			await self.app.shutdown()
			self.server.close()
			self._loop.stop()

		elif command == "clip_select":
			clip_index = params.get('id', 0)
			await self._hyperdeck.select_clip_by_index(clip_index)
		elif command == "clip_refresh":
			await self._hyperdeck.update_clips()
			slots = []
			for s in ['1','2']:
				response = await self._hyperdeck.slotInfo(s)
				if response['lines'][2:][0] == 'status: mounted':
					slots.append(s)
			message = {
				'response': 'sd_slots',
				'params': {
					'slots': slots
				}
			}
			await self._send_websocket_message(message)
		elif command == "clip_previous":
			await self._hyperdeck.select_clip_by_offset(-1)
		elif command == "clip_next":
			await self._hyperdeck.select_clip_by_offset(1)
		elif command == "delete":
			message = {
				'response': 'alert',
				'params': {
					'status': 'File deletion started',
					'action': 'start'
				}
			}
			await self._send_websocket_message(message)
			selectedFile = params.get("sf")
			ftp = ftplib.FTP(self._ip)
			ftp.login()

			# in root to start
			slots = []
			for item in ftp.nlst():
					slots.append(item)

			found = False
			for s in slots:
				if found == False:
					ftp.cwd('/') #start in root
					ftp.cwd('/'+s+'/') #go to each folder/slot in the machine
					files = ftp.nlst()
					for f in files:
						if f == selectedFile:
							ftp.delete(f) #delete the file
					ftp.cwd('/') #end in root
				else:
					break
			ftp.quit()
			message = {
				'response': 'alert',
				'params': {
					'status': 'File deletion complete',
					'action': 'close'
				}
			}
			await self._send_websocket_message(message)
		elif command == "download":
			message = {
				'response': 'alert',
				'params': {
					'status': 'Download started',
					'action': 'start'
				}
			}
			await self._send_websocket_message(message)

			global progress
			progress = 0

			root = tk.Tk()
			width = 300
			height = 50
			screen_width = root.winfo_screenwidth()
			screen_height = root.winfo_screenheight()
			x = (screen_width/2) - (width/2)
			y = (screen_height/2) - (height/2)

			root.geometry('%dx%d+%d+%d' % (width,height,x,y))
			root.attributes("-topmost", True)
			root.title('Video Transfer Progress')

			#def update_progress_label():
				#return f"{pb['value']}%"

			def progressUpdate(num):
				if num < 100:
					#value_label['text'] = update_progress_label()
					pb['value'] = round(num)
				else:
					stop()

			def start(block, fileToWrite, total_size):
				handleDownload(block, fileToWrite, total_size)

			def stop():
				pb.stop()
				#value_label['text'] = update_progress_label()
				root.quit()
				root.destroy()

			root.iconbitmap('WebUI/Resources/favicon.ico')
			TROUGH_COLOR = '#161616'
			BAR_COLOR = '#f5a623'
			s = ttk.Style()
			s.theme_use('clam')
			s.configure("bar.Horizontal.TProgressbar",troughcolor=TROUGH_COLOR, background=BAR_COLOR, lightcolor=BAR_COLOR, darkcolor=BAR_COLOR)
			
			pb = ttk.Progressbar(
				root,
				style="bar.Horizontal.TProgressbar",
				orient='horizontal',
				mode='determinate',
				length=280
			)

			pb.grid(column=0,row=1,columnspan=2,padx=10,pady=20)
			#value_label = ttk.Label(root, text=update_progress_label())
			#value_label.grid(column=0,row=1,columnspan=2)

			
			def handleDownload(block, fileToWrite, ts):

				fileToWrite.write(block)
				global progress
				if progress == 0:
					pb.start()
				progress = progress + len(block)
				progressUpdate((progress/ts)*100)
				root.update()


			selectedFile = params.get("sf")
			ftp = ftplib.FTP(self._ip)
			ftp.login()

			# in root to start
			slots = []
			for item in ftp.nlst():
					slots.append(item)

			found = False
			for s in slots:
				if found == False:
					ftp.cwd('/') #start in root
					ftp.cwd('/'+s+'/') #go to each folder/slot in the machine
					files = ftp.nlst()
					for f in files:
						if f == selectedFile:
							found = True
							try:
								currentDir = os.getcwd()
								os.chdir(self._local_download_folder)
								total_size = ftp.size(f)
								fileToWrite = open(f, 'wb')
								ftp.retrbinary("RETR " + f ,lambda block: start(block, fileToWrite, total_size))
								root.mainloop()
								webbrowser.open(self._local_download_folder)
								os.chdir(currentDir)
							except:
								print ("Error")
							break
					ftp.cwd('/') #end in root
				else:
					break
			ftp.quit()
			message = {
				'response': 'alert',
				'params': {
					'status': 'Download complete',
					'action': 'close'
				}
			}
			await self._send_websocket_message(message)
			
			
		await self.loading(False)

	async def _send_websocket_message(self, message):
		if self._websocket is None or self._websocket.closed:
			return None

		message_json = json.JSONEncoder().encode(message)

		self.logger.debug("Front-end response: {}".format(message_json))
		response = await self._websocket.send_str(message_json)
		return response

	async def _hyperdeck_event(self, event, params=None):
		# HyperDeck state change event handlers, one per supported event type.
		event_handlers = {
			'clips': self._hyperdeck_event_clips_changed,
			'status': self._hyperdeck_event_status_changed,
			'transcript': self._hyperdeck_event_transcript,
		}

		handler = event_handlers.get(event)
		if handler is not None:
			await handler(params)

	async def _hyperdeck_event_clips_changed(self, params):
		# The commented below seemed more complicated
		message = {
			'response':'clip_list',
			'params': {
				'clips': self._hyperdeck.clips
			}
		}
		await self._send_websocket_message(message)
		'''
		# First send a new clip count update. this clears the clip list in the
		# front-end and prepares it to receive new clip entries/
		message = {
			'response': 'clip_count',
			'params': {
				'count': len(self._hyperdeck.clips)
			}
		}
		await self._send_websocket_message(message)

		# Next, send through clip info updates to the front-end, one per clip.
		for index, clip in enumerate(self._hyperdeck.clips):
			message = {
				'response': 'clip_info',
				'params': {
					'id': index, #this originally had + 1 but JS subtracted 1...
					'name': clip['name'],
					'timecode': clip['timecode'],
					'duration': clip['duration'][:-3]
				}
			}
			await self._send_websocket_message(message)'''

	async def _hyperdeck_event_status_changed(self, params):
		# Send the new HyperDeck status to the front-end for display.
		message = {
			'response': 'status',
			'params': self._hyperdeck.status
		}
		await self._send_websocket_message(message)

	async def _hyperdeck_event_transcript(self, params):
		# Send through the communication log to the front-end, so that it can
		# display the transcript to the user.
		message = {
			'response': 'transcript',
			'params': params
		}
		await self._send_websocket_message(message)