from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
import math
import random
from boid import Boid, PVector

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
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.radius = 50.0
        self.x = random.uniform(self.radius, visualizer.width - self.radius*2)
        self.y = random.uniform(self.radius, visualizer.height - self.radius*2)
        
    def add_chunk(self, chunk):
        chunk.duration = max(chunk.duration, MIN_SOUNDING_DURATION)
        chunk.boid = Boid(self.get_departure_position(chunk), 10.0, 3.0)
        chunk.arrival_position = self.get_arrival_position(chunk)
        chunk.boid.arrive(chunk.arrival_position)
        chunk.arrived = False
        chunk.playing = False
        self.arriving_chunks[chunk.id] = chunk

    def get_departure_position(self, chunk):
        if chunk.pan < 0.5:
            x = 0
        else:
            x = self.visualizer.width
        y = chunk.height * self.visualizer.height
        return PVector(x, y)

    def get_arrival_position(self, chunk):
        angle = 2 * math.pi * chunk.begin / chunk.file_length
        x = self.x + self.radius * math.cos(angle)
        y = self.y + self.radius * math.sin(angle)
        return PVector(x, y)
        
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
            if not chunk.arrived:
                if self.arrived(chunk):
                    self.play_chunk(chunk)
                    chunk.arrived = True
                    chunk.playing = True
                    chunk.started_playing = self.now
            if chunk.arrived:
                if chunk.playing:
                    if self.now - chunk.started_playing > chunk.duration:
                        del f.arriving_chunks[chunk.id]
                        f.gatherer.add(chunk)

    def arrived(self, chunk):
        distance = chunk.arrival_position.sub(chunk.boid.loc).mag()
        return distance < 1.0
        
    def draw_gathered_chunks(self, f):
        for chunk in f.gatherer.pieces():
            self.draw_completed_piece(chunk, f)

    def draw_arriving_chunks(self, f):
        for chunk in f.arriving_chunks.values():
            self.draw_chunk(chunk, f)

    def draw_chunk(self, chunk, f):
        if chunk.playing:
            self.draw_sounding_chunk(chunk, f)
        else:
            self.draw_travelling_chunk(chunk, f)

    def draw_travelling_chunk(self, chunk, f):
        chunk.boid.update()
        self.draw_boid(chunk.boid)

    def draw_boid(self, boid):
        size = 1
        x1 = boid.loc.x - size
        x2 = boid.loc.x + size
        y1 = boid.loc.y - size
        y2 = boid.loc.y + size
        opacity = 0.3
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_POLYGON)
        glVertex2f(x1, y1)
        glVertex2f(x1, y2)
        glVertex2f(x2, y2)
        glVertex2f(x2, y1)
        glVertex2f(x1, y1)
        glEnd()

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
