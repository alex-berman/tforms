from visualizer import Visualizer, run
from OpenGL.GL import *
from boid import Boid, PVector

class Steering(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.boids = []
        boid = Boid(PVector(10, 10), 3.0, 3.0)
        boid.arrive(PVector(400, 200))
        self.boids.append(boid)

    def render(self):
        for boid in self.boids:
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
