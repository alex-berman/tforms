import math
import copy

class PVector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def add(self, other):
        return PVector(self.x + other.x,
                       self.y + other.y)

    def sub(self, other):
        return PVector(self.x - other.x,
                       self.y - other.y)

    def mult(self, factor):
        self.x *= factor
        self.y *= factor

    def mag(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        m = self.mag()
        self.x /= m
        self.y /= m

    def limit(self, desired_magnitude):
        m = self.mag()
        if m > desired_magnitude:
            self.mult(desired_magnitude / m)

class Boid:
    def __init__(self, l, maxspeed, maxforce):
        self.target = None
        self.vel = PVector(0,0)
        self.loc = copy.copy(l)
        self.maxspeed = maxspeed
        self.maxforce = maxforce

    def update(self):
        acc = self.steer(self.target, True)
        self.vel = self.vel.add(acc)
        self.vel.limit(self.maxspeed)
        self.loc = self.loc.add(self.vel)

    def arrive(self, target):
        self.target = target

    def steer(self, target, slowdown):
        desired = target.sub(self.loc)
        d = desired.mag()
        if d > 0:
            desired.normalize()
            if slowdown and d < 100:
                desired.mult(self.maxspeed*(d/100))
            else:
                desired.mult(self.maxspeed)
            steer = desired.sub(self.vel)
            steer.limit(self.maxforce)
        else:
            steer = PVector(0,0)
        return steer
