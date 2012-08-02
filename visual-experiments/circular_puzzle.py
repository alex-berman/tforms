from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector
import random
import math
import colorsys

DURATION = 0.5
CIRCLE_PRECISION = 10

class File:
    def __init__(self, filenum, length, visualizer):
        self.filenum = filenum
        self.length = length
        self.visualizer = visualizer
        self.gatherer = Gatherer()
        self.inner_radius = 50.0
        self.outer_radius = self.inner_radius + 5.0
        self.x = random.uniform(self.outer_radius, visualizer.width - self.outer_radius*2)
        self.y = random.uniform(self.outer_radius, visualizer.height - self.outer_radius*2)

    def add_chunk(self, chunk):
        self.gatherer.add(chunk)

    def draw(self):
        for chunk in self.gatherer.pieces():
            self.draw_completed_piece(chunk)

    def draw_completed_piece(self, chunk):
        num_vertices = int(CIRCLE_PRECISION * float(chunk.end - chunk.begin) / chunk.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(1)
        opacity = 0.5
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_LOOP)

        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(i) / (num_vertices-1)
            x, y = self.completion_position(chunk, byte_position, self.inner_radius)
            glVertex2f(x, y)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(num_vertices-i-1) / (num_vertices-1)
            x, y = self.completion_position(chunk, byte_position, self.outer_radius)
            glVertex2f(x, y)

        glEnd()

    def completion_position(self, chunk, byte_position, radius):
        angle = 2 * math.pi * byte_position / chunk.file_length
        x = self.x + radius * math.cos(angle)
        y = self.y + radius * math.sin(angle)
        return x, y

class Puzzle(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.files = {}

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.filenum, chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

        self.play_chunk(chunk)

    def render(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for f in self.files.values():
            f.draw()
        glDisable(GL_LINE_SMOOTH)
        glDisable(GL_BLEND)

run(Puzzle)
