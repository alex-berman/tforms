from vector import Vector2d
import random
import math

class Sway:
    # def __init__(self):
    #     self.sway = Vector2d(0, 0)
    #     self.sway_force = Vector2d(0, 0)
    #     self.pullback_force = Vector2d(0, 0)

    # def update(self, time_increment):
    #     delta = min(time_increment, 1)
    #     self.sway_force += self.random_vector() * 0.001 * delta
    #     self.sway_force.limit(0.001)
    #     self.pullback_force -= self.sway * delta * 0.05
    #     self.sway += self.sway_force
    #     self.sway += self.pullback_force

    # def random_vector(self):
    #     return Vector2d(random.uniform(-0.5, 0.5),
    #                     random.uniform(-0.5, 0.5))

    def __init__(self, magnitude=0.005, min_speed=0.5, max_speed=0.9):
        self.magnitude = magnitude
        self.t1 = random.uniform(0, 2*math.pi)
        self.t2 = random.uniform(0, 2*math.pi)
        self.speed1 = random.uniform(min_speed, max_speed)
        self.speed2 = random.uniform(min_speed, max_speed)
        self.sway = Vector2d(0, 0)
        self.update(0)

    def update(self, time_increment):
        self.t1 += time_increment * self.speed1
        self.t2 += time_increment * self.speed2
        self.sway.x = math.cos(self.t1) * self.magnitude
        self.sway.y = math.sin(self.t2) * self.magnitude
