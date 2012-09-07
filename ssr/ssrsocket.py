
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

	def collect_incoming_data( self, data ):
		self.data = self.data + data

	def found_terminator( self ):
		self.handle_data( self.data )
		self.data = ''

	def handle_data( self, data ):
		self.callback( data )


class AIOThread( Thread ):
	def __init__( self, host, port, callback ):
		Thread.__init__( self )
		self.daemon = True
		self.ssrsock = SSRSocket( host, port, callback )
		self.quit = False
		self._lock = Lock()

	def run( self ):
		while( not self.quit ):
			with self._lock:
				asyncore.loop( 0.1, False, None, 1 )


	def push( self, str ):
		with self._lock:
			self.ssrsock.push( str )

	def stop( self ):
		self.quit = True
		self.ssrsock.close()

