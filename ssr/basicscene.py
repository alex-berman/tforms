import time

class Source:
	def __init__( self, scene, id, x, y ):
		self.scene = scene
		self.id = id
		self.x = float(x)
		self.y = float(y)
		self.type = "point"
		self.orientation = float(0)
		self.mute = False
		self.name = "Unnamed"
		self.volume = 0.0 # in dB
		self.level = 0.0
		self.allocated = False
		self.movement_start_time = None

	def start_movement(self, start_position, end_position, movement_duration):
		self.movement_start_time = time.time()
		self.start_position = start_position
		self.end_position = end_position
		self.movement_duration = movement_duration

	def update(self):
		if self.movement_start_time is not None:
			relative_age = (time.time() - self.movement_start_time) / self.movement_duration
			if relative_age < 1:
				new_position = self.start_position + \
				    (self.end_position - self.start_position) * relative_age
				self.request_position(new_position)
			elif self.allocated:
#				self.request_mute()
				self.movement_start_time = None
				self.allocated = False

	def request_position(self, position):
		self.scene.ssr_socket.push(
                        '<request><source id="%d"><position x="%f" y="%f"/></source></request>\0' % (
				self.id, position.x, position.y))

#	def request_mute(self, position):

class Speaker:
	def __init__( self, x, y, azimuth ):
		self.x = float(x)
		self.y = float(y)
		self.azimuth = float(azimuth)

class Reference:
	def __init__( self ):
		self.x = 0.0
		self.y = 0.0
		self.azimuth = 0.0

class BasicScene:
	def __init__( self ):
		self.sources = {}
		self.speakers = []
		self.reference = Reference()
	

	def set_reference_position( self, x, y ):
		self.reference.x = x
		self.reference.y = y

	def set_reference_orientation( self, azimuth ):
		self.reference.azimuth = azimuth

	def set_source_position( self, id, x, y ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, x, y )
		else:
			self.sources[id].x = float(x)
			self.sources[id].y = float(y)
	
	def set_source_model( self, id, type ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].type = type

	def set_source_orientation( self, id, azimuth ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].azimuth = azimuth

	def set_source_name( self, id, name ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].name = name

	def set_source_volume( self, id, vol ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].volume = vol

	def set_source_level( self, id, level ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].level = level

	def set_source_mute( self, id, mute ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( self, id, 0, 0 )
	
		self.sources[id].mute = mute

	def add_speaker( self, x, y, azimuth ):
			self.speakers.append( Speaker( x, y, azimuth ) )


