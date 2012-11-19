import visualizer
from visualizer import File, run
from vector import DirectionalVector, Vector2d
import math

class Chunk:
    def peer_position(self):
        return Visualizer.bearing_to_border_position(
            self.peer.bearing, self.visualizer.width, self.visualizer.height)

class Segment(visualizer.Segment, Chunk):
    pass

class Peer(visualizer.Peer):
    pass

class Visualizer(visualizer.Visualizer):
    @staticmethod
    def bearing_to_border_position(bearing, width, height):
        radius = math.sqrt(width*width + height*height) / 2
        midpoint = Vector2d(width/2, height/2)
        circle_position = midpoint + DirectionalVector(bearing - 2*math.pi/4, radius)
        return circle_position

    def pan_segment(self, segment):
        relative_x = segment.pan
        space_y = 3
        space_x = (relative_x - 0.5) * 5
        self.orchestra.place_segment(segment.id, space_x, space_y, segment.duration)
