import math
import random
from vector import Vector2d, DirectionalVector
from bezier import make_bezier

class Space:
    LISTENER_POSITION = Vector2d(0, 0)
    ROOM_RADIUS = 30
    NEAREST_DISTANCE_TO_LISTENER = 0.1
    MIN_CURVATURE = 50.0 / 360 * 2*math.pi
    MAX_CURVATURE = 80.0 / 360 * 2*math.pi
    TRAJECTORY_PRECISION = 300

    def new_peer(self):
        return Peer(self)

    def parabolic_trajectory_to_listener(self, remote_angle):
        remote = DirectionalVector(remote_angle, self.ROOM_RADIUS)
        midpoint_angle = remote_angle + random.choice([1,-1]) * \
            random.uniform(self.MIN_CURVATURE, self.MAX_CURVATURE)
        midpoint = DirectionalVector(midpoint_angle, self.ROOM_RADIUS/2)
        local = self.LISTENER_POSITION + \
            DirectionalVector(remote_angle, self.NEAREST_DISTANCE_TO_LISTENER)
        control_points = [(remote.x, remote.y),
                          (midpoint.x, midpoint.y),
                          (local.x, local.y)]
        bezier = make_bezier(control_points)
        return bezier(self.TRAJECTORY_PRECISION)

class Peer:
    def __init__(self, space):
        self.space = space
        self.bearing = random.uniform(0.0, 2*math.pi)
