import ssrsocket
import time
import packetParser
import basicscene
import threading

HOSTNAME = "localhost"
PORT = 4711

class SsrControl:
    def __init__(self, num_sources=16):
        self.num_sources = num_sources
        self.scene = basicscene.BasicScene()
        self.scene.smooth_movement_enabled = False
        self.updated = False
        pp = packetParser.PacketParser( self.scene, self.update )
        self.ssr_socket = ssrsocket.AIOThread( HOSTNAME, PORT, pp.parse_packet )
        self.scene.ssr_socket = self.ssr_socket
        self.ssr_socket.start()
        self._add_sources_if_needed()

    def enable_smooth_movement(self):
        self.scene.smooth_movement_enabled = True
        self._mute_all_sources()
        self._start_movement_thread()

    def update(self):
        self.updated = True

    def _add_sources_if_needed(self):
        while not self.updated:
            time.sleep(0.1)
        if self.num_sources > len(self.scene.sources):
            self._add_sources()

    def _add_sources(self):
        num_sources_to_add = self.num_sources - len(self.scene.sources)
        print "requesting to add %d sources" % num_sources_to_add
        for i in range(num_sources_to_add):
            self.ssr_socket.push('<request><source new="true" name="source%d" port="SuperCollider:out_%d" volume="-6"><position fixed="false"/></source></request>\0' % (i, i+1))

        print "waiting for sources to be added"
        while len(self.scene.sources) < self.num_sources:
            time.sleep(0.1)
        print "OK"

    def _mute_all_sources(self):
        for source in self.scene.sources.values():
            source.request_mute("true")

    def _start_movement_thread(self):
        thread = threading.Thread(target=self._move_sources)
        thread.daemon = True
        thread.start()

    def _move_sources(self):
        while True:
            for source in self.scene.sources.values():
                source.update()
            time.sleep(0.01)

    def start_source_movement(self, source_id, trajectory, duration):
        self.scene.sources[source_id].start_movement(trajectory, duration)

    def allocate_source(self):
        for source_id, source in self.scene.sources.iteritems():
            if not source.allocated:
                source.allocated = True
                return source_id

    def free_source(self, source_id):
        self.scene.sources[source_id].allocated = False

    def place_source(self, source_id, x, y, duration):
        self.free_completed_placed_sources()
        self.scene.sources[source_id].place_at(x, y, duration)

    def free_completed_placed_sources(self):
        for source_id, source in self.scene.sources.iteritems():
            source.free_if_completed_placement()
