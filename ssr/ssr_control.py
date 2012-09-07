import ssrsocket
import time
import packetParser
import basicscene
from vector import Vector2d, DirectionalVector
import math
import random
import threading

HOSTNAME = "localhost"
PORT = 4711

class SsrControl:
    LISTENER_POSITION = Vector2d(0, 0)
    ROOM_RADIUS = 3

    def __init__(self, num_sources=16):
        self.num_sources = num_sources
        self.scene = basicscene.BasicScene()
        def update(): pass
        pp = packetParser.PacketParser( self.scene, update )
        self.ssr_socket = ssrsocket.AIOThread( HOSTNAME, PORT, pp.parse_packet )
        self.ssr_socket.start()
        self._add_sources()
        self._start_movement_thread()

    def _start_movement_thread(self):
        thread = threading.Thread(target=self._move_sources)
        thread.daemon = True
        thread.start()

    def _move_sources(self):
        while True:
            for source_id, source in self.scene.sources.iteritems():
                position = source.current_position()
                if position:
                    self.ssr_socket.push(
                        '<request><source id="%d"><position x="%f" y="%f"/></source></request>\0' % (
                            source_id, position.x, position.y))
            time.sleep(0.1)

    def _add_sources(self):
        print "requesting to add sources"
        for i in range(self.num_sources):
            self.ssr_socket.push('<request><source new="true" name="source%d" port="SuperCollider:out_%d" volume="-6"><position fixed="false"/></source></request>\0' % (i, i+1))

        print "waiting for sources to be added"
        while len(self.scene.sources) < self.num_sources:
            time.sleep(0.1)
        print "OK"

    def start_source_movement(self, source_id, start_position, end_position, duration):
        self.scene.sources[source_id].start_movement(start_position, end_position, duration)

    def random_position(self):
        angle = random.uniform(0, 2*math.pi)
        return DirectionalVector(angle, self.ROOM_RADIUS)

    def allocate_source(self):
        for source_id, source in self.scene.sources.iteritems():
            if not source.allocated:
                source.allocated = True
                return source_id
        raise Exception("failed to allocate source")

    def free_source(self, source_id):
        self.scene.sources[source_id].allocated = False
