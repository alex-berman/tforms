import time

class Source:
	def __init__( self, scene, id, x=0, y=0):
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
		self.movement_started = False
		self.movement_start_time = None
		self.placed_at_time = None

	def set_position(self, x, y):
		self.x = float(x)
		self.y = float(y)
		self.received_position()

	def start_movement(self, trajectory, movement_duration):
		self.movement_started = False
		self.movement_start_time = time.time()
		self.trajectory = trajectory
		self.movement_duration = movement_duration

	def update(self):
		if self.movement_start_time is not None:
			relative_age = (time.time() - self.movement_start_time) / self.movement_duration
			if relative_age < 1:
				new_position = self.trajectory[
					int(relative_age * len(self.trajectory))]
				self.request_position(new_position[0], new_position[1])
			elif self.allocated:
				self.request_mute("true")
				self.movement_start_time = None
				self.allocated = False

	def place_at(self, x, y, duration):
		self.placement_duration = duration
		self.placed_at_time = time.time()
		self.request_position(x, y)

	def free_if_completed_placement(self):
            if self.placed_at_time and (time.time() - self.placed_at_time) > self.placement_duration:
		    self.allocated = False

	def request_position(self, x, y):
		self.scene.ssr_socket.push(
                        '<request><source id="%d"><position x="%f" y="%f"/></source></request>\0' % (
				self.id, x, y))

	def received_position(self):
		if self.scene.smooth_movement_enabled and not self.movement_started:
			self.request_mute("false")
			self.movement_started = True

	def request_mute(self, value):
		self.scene.ssr_socket.push(
                        '<request><source id="%d" mute="%s"/></request>\0' % (
				self.id, value))

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

	def ensure_source_exists(self, id):
		if not id in self.sources:
			self.sources[id] = Source(self, id)

	def set_reference_position( self, x, y ):
		self.reference.x = x
		self.reference.y = y

	def set_reference_orientation( self, azimuth ):
		self.reference.azimuth = azimuth

	def set_source_position( self, id, x, y ):
		self.sources[id].set_position(x, y)
	
	def set_source_model( self, id, type ):
		self.sources[id].type = type

	def set_source_orientation( self, id, azimuth ):
		self.sources[id].azimuth = azimuth

	def set_source_name( self, id, name ):
		self.sources[id].name = name

	def set_source_volume( self, id, vol ):
		self.sources[id].volume = vol

	def set_source_level( self, id, level ):
		self.sources[id].level = level

	def set_source_mute( self, id, mute ):
		self.sources[id].mute = mute

	def add_speaker( self, x, y, azimuth ):
		self.speakers.append( Speaker( x, y, azimuth ) )
