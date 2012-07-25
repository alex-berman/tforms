from visualizer import Visualizer, run
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
import math
import random
from boid import Boid, PVector

CIRCLE_PRECISION = 10
CHUNK_SIZE_FACTOR = 0.000001
SOUNDING_CHUNK_SIZE_FACTOR = CHUNK_SIZE_FACTOR * 1.5
MAX_CHUNK_SIZE = 5.0 / 640

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.radius = 50.0
        self.x = random.uniform(self.radius, visualizer.width - self.radius*2)
        self.y = random.uniform(self.radius, visualizer.height - self.radius*2)
        
    def add_chunk(self, chunk):
        chunk.boid = Boid(self.get_departure_position(chunk), 10.0, 3.0)
        chunk.arrival_position = self.get_arrival_position(chunk)
        chunk.boid.arrive(chunk.arrival_position)
        chunk.arrived = False
        self.arriving_chunks[chunk.id] = chunk

    def stopped_playing(self, chunk_id):
        chunk = self.arriving_chunks[chunk_id]
        del self.arriving_chunks[chunk_id]
        self.gatherer.add(chunk)

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

    def InitGL(self):
        Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

    def stopped_playing(self, chunk_id, filenum):
        self.files[filenum].stopped_playing(chunk_id)

    def render(self):
        for f in self.files.values():
            self.process_chunks(f)
        self.draw_gathered_chunks()
        self.draw_arriving_chunks()
        self.draw_sounding_chunks()

    def process_chunks(self, f):
        for chunk in f.arriving_chunks.values():
            if not chunk.arrived:
                chunk.boid.update()
                if self.arrived(chunk):
                    self.play_chunk(chunk)
                    chunk.arrived = True

    def arrived(self, chunk):
        distance = chunk.arrival_position.sub(chunk.boid.loc).mag()
        return distance < 1.0
        
    def draw_gathered_chunks(self):
        for f in self.files.values():
            for chunk in f.gatherer.pieces():
                self.draw_completed_piece(chunk, f)

    def draw_arriving_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                if not chunk.playing:
                    self.draw_travelling_chunk(chunk, f)

    def draw_sounding_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                if chunk.playing:
                    self.draw_sounding_chunk(chunk, f)

    def draw_travelling_chunk(self, chunk, f):
        opacity = 0.3
        size = chunk.byte_size * CHUNK_SIZE_FACTOR * self.width
        self.draw_point(chunk.boid.loc.x,
                        chunk.boid.loc.y,
                        size, opacity)

    def draw_point(self, x, y, size, opacity):
        size = min(size, MAX_CHUNK_SIZE * self.width)
        size = max(size, 1.0)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    def draw_completed_piece(self, chunk, f):
        opacity = 0.3
        self.draw_sitting_piece(chunk, f, opacity)

    def draw_sounding_chunk(self, chunk, f):
        opacity = 1
        size = chunk.byte_size * SOUNDING_CHUNK_SIZE_FACTOR * self.width
        mid_byte = (chunk.begin + chunk.end) / 2
        x, y = self.completion_position(chunk, mid_byte, f)
        self.draw_point(x, y, size, opacity)

    def draw_sitting_piece(self, chunk, f, opacity):
        num_vertices = int(CIRCLE_PRECISION * float(chunk.end - chunk.begin) / chunk.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(4)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_STRIP)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(i) / (num_vertices-1)
            x, y = self.completion_position(chunk, byte_position, f)
            glVertex2f(x, y)
        glEnd()

    def completion_position(self, chunk, byte_position, f):
        angle = 2 * math.pi * byte_position / chunk.file_length
        x = f.x + f.radius * math.cos(angle)
        y = f.y + f.radius * math.sin(angle)
        return x, y

run(Puzzle)
