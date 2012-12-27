from vector import Vector2d
import random

class Sway:
    def __init__(self):
        self.sway = Vector2d(0, 0)
        self.sway_force = Vector2d(0, 0)
        self.pullback_force = Vector2d(0, 0)

    def update(self, time_increment):
        delta = min(time_increment, 1)
        self.sway_force += self.random_vector() * 0.001 * delta
        self.sway_force.limit(0.001)
        self.pullback_force -= self.sway * delta * 0.05
        self.sway += self.sway_force
        self.sway += self.pullback_force

    def random_vector(self):
        return Vector2d(random.uniform(-0.5, 0.5),
                        random.uniform(-0.5, 0.5))

