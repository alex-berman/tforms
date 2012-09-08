
from xml.dom.minidom import parseString
from math import log

fact=20/log(10)
cap = -40

# def linear2db( x ):
# 	if( x==0 ):
# 		return cap 
# 	return max( cap, fact*log(x) )


class PacketParser:
	def __init__( self, scene, update_cb ):
		self.update = update_cb
		self.scene = scene

	def parse_packet( self, data ):
		doc = parseString( data )
		rootnode = doc.documentElement
		if rootnode.tagName == "update":
			self.parse_update( rootnode )


	def parse_update( self, node ):
		for i in node.childNodes:
			if i.tagName == "source":
				self.parse_source( i )
			elif i.tagName == "loudspeaker":
				self.parse_speaker( i )
			elif i.tagName == "reference":
				self.parse_reference( i )
			elif i.tagName == "delete":
				self.parse_delete( i )

		self.update()

	def parse_delete( self, node ):
		for i in node.childNodes:
			if i.tagName == "source":
				id = int( i.attributes["id"].value )
				if id==0:
					self.scene.sources={}
				else:
					del self.scene.source[id]


	def parse_reference( self, node ):
		for i in node.childNodes:
			if i.tagName == "position":
				if ("x" in i.attributes.keys()) and ("y" in i.attributes.keys()):
					x = float(i.attributes["x"].value)
					y = float(i.attributes["y"].value)
					self.scene.set_reference_position( x, y )
			elif i.tagName == "orientation":
				az = float(i.attributes["azimuth"].value)
				self.scene.set_reference_orientation( az )

	def parse_source( self, node ):
		id = int(node.attributes["id"].value)
		if "name" in node.attributes.keys():
			self.scene.set_source_name( id, node.attributes["name"].value )
		if "volume" in node.attributes.keys():
			#print node.attributes["volume"].value
			#print linear2db( float(node.attributes["volume"].value) )
			#print float(node.attributes["volume"].value)
			#self.scene.set_source_volume( id, linear2db( float(node.attributes["volume"].value) ) )
			self.scene.set_source_volume( id, float(node.attributes["volume"].value) )
		if "level" in node.attributes.keys():
			self.scene.set_source_level( id, float(node.attributes["level"].value) )
		if "model" in node.attributes.keys():
			self.scene.set_source_model( id, node.attributes["model"].value )
		if "mute" in node.attributes.keys():
			if node.attributes["mute"].value == "true":
				self.scene.set_source_mute( id, True )
			else:
				self.scene.set_source_mute( id, False )

		for i in node.childNodes:
			if i.tagName == "position":
				if ("x" in i.attributes.keys()) and ("y" in i.attributes.keys()):
					x = float(i.attributes["x"].value)
					y = float(i.attributes["y"].value)
					#print "Source %d -> (%f, %f)" % (id, x, y)
					self.scene.set_source_position( id, x, y )
			elif i.tagName == "orientation":
				az = float(i.attributes["azimuth"].value)
				self.scene.set_source_orientation( id, az )
			elif i.tagName == "delete":
				if id==0:
					self.scene.sources={}
				else:
					del self.scene.source[id]

	def parse_speaker( self, node ):
		x = 0.0
		y = 0.0
		az = 0.0
		for i in node.childNodes:
			if i.tagName == "position":
				x = float(i.attributes["x"].value)
				y = float(i.attributes["y"].value)
			elif i.tagName == "orientation":
				az = float(i.attributes["azimuth"].value)

		#print "Speaker (%f, %f o %f)" % (x, y, az)
		self.scene.add_speaker( x, y, az )

