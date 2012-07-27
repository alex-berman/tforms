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
threading.Thread(target=visualizer.run).start()

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
    
sleep(1); add_chunk(0, 1000, 2000)
sleep(1); add_chunk(0, 2000, 3000)
sleep(0.1); add_chunk(0, 3000, 4000)
sleep(0.1); add_chunk(0, 4000, 5000)

sleep(2); add_chunk(0, 10000, 11000)
