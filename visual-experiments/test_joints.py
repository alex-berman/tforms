import threading
from time import sleep
import time
import joints
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-sync', action='store_true')
parser.add_argument('-width', dest='width', type=int, default=640)
parser.add_argument('-height', dest='height', type=int, default=480)
parser.add_argument('-show-fps', dest='show_fps', action='store_true')
args = parser.parse_args()
visualizer = joints.Joints(args)
visualizer_thread = threading.Thread(target=visualizer.run)
visualizer_thread.daemon = True
visualizer_thread.start()

id_count = 0
files = [{"offset": 0,
          "length": 10,
          "pan": -1,
          "height": 0.3}]

def add_chunk(filenum, begin, end):
    global id_count
    chunk_id = id_count
    id_count += 1
    file = files[filenum]
    torrent_position = begin
    byte_size = end - begin
    chunk = joints.Chunk(
        chunk_id, torrent_position, byte_size,
        filenum, file["offset"], file["length"], file["pan"], file["height"], time.time(), visualizer)
    visualizer.add_chunk(chunk)
    
sleep(1);

for i in range(100):
    add_chunk(0, 1000 + i*10, 1000 + (i+1)*10)
    sleep(0.1)

while(True): sleep(1.0)
