import threading
from time import sleep
import time
import circular_puzzle
import argparse
from visualizer import Chunk
from vector import Vector

#positions = [Vector(150, 150), Vector(360, 150)]
#positions = [Vector(150, 150), Vector(330, 150)]
#positions = [Vector(150, 150), Vector(460, 150)]
#positions = [Vector(150, 150), Vector(580, 150)]
#positions = [Vector(360, 150), Vector(150, 150)]
#positions = [Vector(330, 150), Vector(150, 150)]
positions = [Vector(110, 150), Vector(580, 150)]

# positions = [Vector(501.145936085, 357.560708033),
#              Vector(117.841625378, 443.805921172),
#              Vector(346.567172083, 108.980287821)]

# positions = [Vector(150, 150),
#              Vector(330, 150),
#              Vector(200, 200)]

class Puzzle(circular_puzzle.Puzzle):
    def random_position(self):
        return positions[len(self.files)]

parser = argparse.ArgumentParser()
parser.add_argument('-sync', action='store_true')
parser.add_argument('-width', dest='width', type=int, default=640)
parser.add_argument('-height', dest='height', type=int, default=480)
parser.add_argument('-show-fps', dest='show_fps', action='store_true')
args = parser.parse_args()
visualizer = Puzzle(args)
threading.Thread(target=visualizer.run).start()

id_count = 0
files = [{"offset": 0,
          "length": 2000,
          "pan": -1,
          "height": 0.3},
         {"offset": 0,
          "length": 2000,
          "pan": -1,
          "height": 0.3},
         {"offset": 0,
          "length": 2000,
          "pan": -1,
          "height": 0.3},
         ]

def add_chunk(filenum, begin, end):
    global id_count
    chunk_id = id_count
    id_count += 1
    file = files[filenum]
    torrent_position = begin
    byte_size = end - begin
    peer_id = 0
    chunk = Chunk(
        chunk_id, torrent_position, byte_size,
        filenum, file["offset"], file["length"], peer_id, file["pan"], file["height"], time.time(), visualizer)
    visualizer.add_chunk(chunk)
    
sleep(1);
add_chunk(0, 0, 1000)
add_chunk(0, 1000, 2000)
add_chunk(1, 0, 1000)
add_chunk(1, 1000, 2000)

# add_chunk(2, 0, 1000)
# add_chunk(2, 1000, 2000)
