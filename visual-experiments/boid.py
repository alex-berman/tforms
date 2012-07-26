import copy
from vector import Vector

class Boid:
    def __init__(self, l, maxspeed, maxforce):
        self.target = None
        self.vel = Vector(0,0)
        self.loc = copy.copy(l)
        self.maxspeed = maxspeed
        self.maxforce = maxforce

    def update(self):
        acc = self.steer(self.target, True)
        self.vel += acc
        self.vel.limit(self.maxspeed)
        self.loc += self.vel

    def arrive(self, target):
        self.target = target

    def steer(self, target, slowdown):
        desired = target - self.loc
        d = desired.mag()
        if d > 0:
            desired.normalize()
            if slowdown and d < 100:
                desired *= self.maxspeed*(d/100)
            else:
                desired *= self.maxspeed
            steer = desired - self.vel
            steer.limit(self.maxforce)
        else:
            steer = Vector(0,0)
        return steer
