
import asynchat
import asyncore
from threading import Thread, Lock
import socket
import time


class SSRSocket( asynchat.async_chat ):
	def __init__( self, host, port, callback ):
		self.sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		self.sock.connect( (host, port) )

		asynchat.async_chat.__init__( self, self.sock )
		self.set_terminator( '\0' )
		self.data = ''
		self.callback = callback
		self._lock = Lock()

	def collect_incoming_data( self, data ):
		self.data = self.data + data

	def found_terminator( self ):
		self.handle_data( self.data )
		self.data = ''

	def handle_data( self, data ):
		self.callback( data )

	def initiate_send(self):
		with self._lock:
			asynchat.async_chat.initiate_send(self)

class AIOThread( Thread ):
	def __init__( self, host, port, callback ):
		Thread.__init__( self )
		self.daemon = True
		self.ssrsock = SSRSocket( host, port, callback )
		self.quit = False

	def run( self ):
		while( not self.quit ):
			asyncore.loop( 0.5, False, None, 1 )


	def push( self, str ):
		self.ssrsock.push( str )

	def stop( self ):
		self.quit = True
		self.ssrsock.close()

