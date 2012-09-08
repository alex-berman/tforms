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
    NEAREST_DISTANCE_TO_LISTENER = 0.5

    def __init__(self, num_sources=16):
        self.num_sources = num_sources
        self.scene = basicscene.BasicScene()
        self.updated = False
        pp = packetParser.PacketParser( self.scene, self.update )
        self.ssr_socket = ssrsocket.AIOThread( HOSTNAME, PORT, pp.parse_packet )
        self.ssr_socket.start()
        self._add_sources_if_needed()
        self._start_movement_thread()

    def update(self):
        self.updated = True

    def _add_sources_if_needed(self):
        while not self.updated:
            time.sleep(0.1)
        if self.num_sources > len(self.scene.sources):
            self._add_sources()

    def _add_sources(self):
        print "requesting to add sources"
        for i in range(self.num_sources - len(self.scene.sources)):
            self.ssr_socket.push('<request><source new="true" name="source%d" port="SuperCollider:out_%d" volume="-6"><position fixed="false"/></source></request>\0' % (i, i+1))

        print "waiting for sources to be added"
        while len(self.scene.sources) < self.num_sources:
            time.sleep(0.1)
        print "OK"

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

    def start_source_movement(self, source_id, start_position, duration):
        angle = (start_position - self.LISTENER_POSITION).angle().get()
        end_position = self.LISTENER_POSITION + \
            DirectionalVector(angle, self.NEAREST_DISTANCE_TO_LISTENER)
        self.scene.sources[source_id].start_movement(start_position, end_position, duration)

    def random_position(self):
        angle = random.uniform(0, 2*math.pi)
        return DirectionalVector(angle, self.ROOM_RADIUS)

    def allocate_source(self):
        for source_id, source in self.scene.sources.iteritems():
            if not source.allocated:
                source.allocated = True
                return source_id

    def free_source(self, source_id):
        self.scene.sources[source_id].allocated = False
