

class Source:
	def __init__( self, x, y ):
		self.x = float(x)
		self.y = float(y)
		self.type = "point"
		self.orientation = float(0)
		self.mute = False
		self.name = "Unnamed"
		self.volume = 0.0 # in dB
		self.level = 0.0
		self.allocated = False

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
			self.sources[id] = Source( x, y )
		else:
			self.sources[id].x = float(x)
			self.sources[id].y = float(y)
	
	def set_source_model( self, id, type ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].type = type

	def set_source_orientation( self, id, azimuth ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].azimuth = azimuth

	def set_source_name( self, id, name ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].name = name

	def set_source_volume( self, id, vol ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].volume = vol

	def set_source_level( self, id, level ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].level = level

	def set_source_mute( self, id, mute ):
		if not( id in self.sources.keys() ):
			self.sources[id] = Source( 0, 0 )
	
		self.sources[id].mute = mute

	def add_speaker( self, x, y, azimuth ):
			self.speakers.append( Speaker( x, y, azimuth ) )


