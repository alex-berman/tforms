import visualizer
from visualizer import File, run
from vector import DirectionalVector, Vector2d
import math

class Chunk:
    def peer_position(self):
        return Visualizer.bearing_to_border_position(
            self.peer.spatial_position.bearing, self.visualizer.width, self.visualizer.height)

class Segment(visualizer.Segment, Chunk):
    pass

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.spatial_position = self.visualizer.space.new_peer()
        self.trajectory = self.visualizer.space.parabolic_trajectory_to_listener(
            self.spatial_position.bearing)

class Visualizer(visualizer.Visualizer):
    @staticmethod
    def bearing_to_border_position(bearing, width, height):
        radius = math.sqrt(width*width + height*height) / 2
        midpoint = Vector2d(width/2, height/2)
        circle_position = midpoint + DirectionalVector(bearing - 2*math.pi/4, radius)
        return circle_position

    def pan_segment(self, segment):
        relative_x = segment.pan
        space_y = self.space.NEAREST_DISTANCE_TO_LISTENER
        space_x = (relative_x - 0.5) * self.space.ROOM_RADIUS * 2
        self.ssr.place_source(segment.sound_source_id, space_x, space_y, segment.duration)
