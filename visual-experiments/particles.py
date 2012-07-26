import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector
import copy
import math
import random
from springs import spring_force

CHUNK_SIZE_FACTOR = 0.000001
MAX_CHUNK_SIZE = 5.0 / 640
INNER_MARGIN = 20.0 / 640

class Chunk(visualizer.Chunk):
    def update(self):
        self.force = Vector(0,0)
        self.attract_to_neighbours()
        self.force.limit(0.5)
        self.repel_from_boundaries()
        self.position += self.force

    def repel_from_boundaries(self):
        if self.position.x < self.visualizer.inner_margin:
            self.force += Vector(1,0)
        if self.position.x > (self.visualizer.width - self.visualizer.inner_margin):
            self.force += Vector(-1,0)
        if self.position.y < self.visualizer.inner_margin:
            self.force += Vector(1,0)
        if self.position.y > (self.visualizer.height - self.visualizer.inner_margin):
            self.force += Vector(-1,0)

    def attract_to_neighbours(self):
        for other in self.file.arriving_chunks.values():
            if other != self:
                desired_distance = abs(self.begin - other.begin) * 0.01
                self.force += spring_force(self.position, other.position, desired_distance)

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        
    def add_chunk(self, chunk):
        self.arriving_chunks[chunk.id] = chunk
        chunk.position = self.get_departure_position(chunk)

    def get_departure_position(self, chunk):
        if chunk.pan < 0.5:
            x = 0
        else:
            x = self.visualizer.width
        y = chunk.height * self.visualizer.height
        return Vector(x, y)

    def update(self):
        self.update_arriving_chunks()

    def update_arriving_chunks(self):
        for chunk in self.arriving_chunks.values():
            chunk.update()

class Particles(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, Chunk)
        self.inner_margin = self.width * INNER_MARGIN
        self.files = {}

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        try:
            f = self.files[chunk.filenum]
        except KeyError:
            f = File(chunk.file_length, self)
            self.files[chunk.filenum] = f
        chunk.file = f
        self.files[chunk.filenum].add_chunk(chunk)

    def stopped_playing(self, chunk_id, filenum):
        self.files[filenum].stopped_playing(chunk_id)

    def render(self):
        for f in self.files.values():
            f.update()
        self.draw_arriving_chunks()

    def draw_arriving_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                self.draw_travelling_chunk(chunk, f)

    def draw_travelling_chunk(self, chunk, f):
        opacity = 0.3
        size = chunk.byte_size * CHUNK_SIZE_FACTOR * self.width
        self.draw_point(chunk.position.x,
                        chunk.position.y,
                        size, opacity)

    def draw_point(self, x, y, size, opacity):
        size = min(size, MAX_CHUNK_SIZE * self.width)
        size = max(size, 1.0)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

if __name__ == '__main__':
    visualizer.run(Particles)
