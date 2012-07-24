from visualizer import Visualizer, run
from OpenGL.GL import *
import copy
import math

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
    def __init__(self, l, ms, mf):
        self.acc = PVector(0,0)
        self.vel = PVector(0,0)
        self.loc = copy.copy(l)
        self.r = 3.0
        self.maxspeed = ms
        self.maxforce = mf

    def update(self):
        self.vel = self.vel.add(self.acc)
        self.vel.limit(self.maxspeed)
        self.loc = self.loc.add(self.vel)
        self.acc.mult(0)

    def arrive(self, target):
        self.acc = self.acc.add(self.steer(target, True))

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

class Steering(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.boids = []
        boid = Boid(PVector(10, 10), 3, 3)
        self.boids.append(boid)

    def render(self):
        for boid in self.boids:
            boid.arrive(PVector(100, 200))
            boid.update()
            self.draw_boid(boid)

    def draw_boid(self, boid):
        size = 5
        x1 = boid.loc.x
        x2 = x1 + size
        y1 = boid.loc.y
        y2 = y1 + size
        glBegin(GL_POLYGON)
        glVertex2f(x1, y1)
        glVertex2f(x1, y2)
        glVertex2f(x2, y2)
        glVertex2f(x2, y1)
        glVertex2f(x1, y1)
        glEnd()

run(Steering)
