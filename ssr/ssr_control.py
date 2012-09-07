import ssrsocket
import time
import packetParser
import basicscene

HOSTNAME = "localhost"
PORT = 4711

class SsrControl:
    def __init__(self, num_sources=16):
        def update(): pass
        self.num_sources = num_sources
        self.scene = basicscene.BasicScene()
        pp = packetParser.PacketParser( self.scene, update )
        self.ssr_socket = ssrsocket.AIOThread( HOSTNAME, PORT, pp.parse_packet )
        self.ssr_socket.start()
        self.add_sources()

    def add_sources(self):
        print "requesting to add sources"
        for i in range(self.num_sources):
            channel_id = i + 1
            self.ssr_socket.push('<request><source new="true" name="source%d" port="SuperCollider:out_%d" volume="-6"><position fixed="false"/></source></request>\0' % (channel_id, channel_id))

        print "waiting for sources to be added"
        while len(self.scene.sources) < self.num_sources:
            time.sleep(0.1)
        print "OK"
