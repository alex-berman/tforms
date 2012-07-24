from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
import math
import random

MIN_SOUNDING_DURATION = 0.1
CIRCLE_PRECISION = 10

class Smoother:
    RESPONSE_FACTOR = 5

    def __init__(self):
        self._current_value = None

    def smooth(self, new_value, time_increment):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * \
                self.RESPONSE_FACTOR * time_increment
        else:
            self._current_value = new_value

    def value(self):
        return self._current_value

class File:
    def __init__(self, length, visualizer):
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.radius = 50.0
        self.x = random.uniform(self.radius, visualizer.width - self.radius*2)
        self.y = random.uniform(self.radius, visualizer.height - self.radius*2)

    def add_chunk(self, chunk):
        sounding_duration = chunk.duration - chunk.fade_in
        if sounding_duration < MIN_SOUNDING_DURATION:
            chunk.duration += MIN_SOUNDING_DURATION - sounding_duration
        chunk.age = 0
        self.arriving_chunks[chunk.id] = chunk

class Puzzle(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.files = {}

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

    def render(self):
        if len(self.files) > 0:
            self.draw_chunks()

    def draw_chunks(self):
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        self.process_chunks(f)
        self.draw_gathered_chunks(f)
        self.draw_arriving_chunks(f)

    def process_chunks(self, f):
        for chunk in f.arriving_chunks.values():
            chunk.age = self.now - chunk.arrival_time
            if chunk.age > chunk.duration:
                del f.arriving_chunks[chunk.id]
                f.gatherer.add(chunk)

    def draw_gathered_chunks(self, f):
        for chunk in f.gatherer.pieces():
            self.draw_completed_piece(chunk, f)

    def draw_arriving_chunks(self, f):
        for chunk in f.arriving_chunks.values():
            self.draw_chunk(chunk, f)

    def draw_chunk(self, chunk, f):
        if chunk.age < chunk.fade_in:
            self.draw_travelling_chunk(chunk, f)
        else:
            self.draw_sounding_chunk(chunk, f)

    def draw_travelling_chunk(self, chunk, f):
        pass

    def draw_completed_piece(self, chunk, f):
        opacity = 0.3
        self.draw_sitting_piece(chunk, f, opacity)

    def draw_sounding_chunk(self, chunk, f):
        opacity = 1
        self.draw_sitting_piece(chunk, f, opacity)

    def draw_sitting_piece(self, chunk, f, opacity):
        num_vertices = int(CIRCLE_PRECISION * float(chunk.end - chunk.begin) / chunk.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(4)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_STRIP)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(i) / (num_vertices-1)
            angle = 2 * math.pi * byte_position / chunk.file_length
            x = f.x + f.radius * math.cos(angle)
            y = f.y + f.radius * math.sin(angle)
            glVertex2f(x, y)
        glEnd()

run(Puzzle)
