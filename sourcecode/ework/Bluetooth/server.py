from websocket_server import WebsocketServer
import threading as td
# Called for every client connecting (after handshake)



class wbserver(td.Thread):
	def __init__(self,port):
		td.Thread.__init__(self)
		self._port = port
	def new_client(self,client, server):
		print("New client connected and was given id %d" % client['id'])
		# ~ server.send_message_to_all('{"INFO":"websocket client connect sucessful"}')


	# Called for every client disconnecting
	def client_left(self,client, server):
		print("Client(%d) disconnected" % client['id'])


	# Called when a client sends a message
	def message_received(self,client, server, message):
		if len(message) > 200:
			message = message[:200]+'..'
		print(message)


	def run(self,):
		
		self.server = WebsocketServer(port=self._port,host="0.0.0.0")
		# ~ self.server.set_fn_new_client(self.new_client)
		# ~ self.server.set_fn_client_left(self.client_left)
		self.server.set_fn_message_received(self.message_received)
		self.server.run_forever()

