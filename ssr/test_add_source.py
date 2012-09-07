import ssrsocket
import time
import packetParser
import basicscene

HOSTNAME = "localhost"
PORT = 4711

def update(): pass

scene = basicscene.BasicScene()
pp = packetParser.PacketParser( scene, update )
ss = ssrsocket.AIOThread( HOSTNAME, PORT, pp.parse_packet )
ss.start()
ss.push('<request><source new="true" name="channel1" port="SuperCollider:out_1" volume="-6"><position fixed="false"/></source></request>\0')

while True:
    for source_id in scene.sources.keys():
        ss.push('<request><source id="%d"><position x="%f" y="%f"/></source></request>\0' % (
                source_id, 1.1, 1.5))
        time.sleep(0.1)

ss.stop()
ss.join()
