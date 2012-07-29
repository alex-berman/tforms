from visualizer import Visualizer, run
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
import math
import random
from boid import Boid
from vector import Vector

CIRCLE_PRECISION = 10

class Branch:
    def __init__(self, filenum, file_length, visualizer):
        self.filenum = filenum
        self.file_length = file_length
        self.f = visualizer.files[filenum]

    def target_position(self):
        angle = 2 * math.pi * self.cursor / self.file_length
        x = self.f.x + self.f.radius * math.cos(angle)
        y = self.f.y + self.f.radius * math.sin(angle)
        return Vector(x, y)

class Peer:
    def __init__(self, departure_position, visualizer):
        self.departure_position = departure_position
        self.visualizer = visualizer
        self.branching_position = None
        self.branches = []

    def add_chunk(self, chunk):
        if len(self.branches) == 0:
            self.branching_position = (self.departure_position + chunk.arrival_position) / 2
        branch = self.find_branch(chunk)
        if not branch:
            branch = Branch(chunk.filenum, chunk.file_length, self.visualizer)
            self.branches.append(branch)
        branch.cursor = chunk.end

    def find_branch(self, chunk):
        for branch in self.branches:
            if branch.filenum == chunk.filenum and branch.cursor == chunk.begin:
                return branch

    def draw(self):
        if len(self.branches) > 0:
            glColor3f(0.5, 1.0, 0.5)
            glLineWidth(1.0)
            self.draw_line(self.departure_position, self.branching_position)
            for branch in self.branches:
                self.draw_line(self.branching_position, branch.target_position())

    def draw_line(self, p, q):
        glBegin(GL_LINES)
        glVertex2f(p.x, p.y)
        glVertex2f(q.x, q.y)
        glEnd()

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.gatherer = Gatherer()
        self.radius = 50.0
        self.x = random.uniform(self.radius, visualizer.width - self.radius*2)
        self.y = random.uniform(self.radius, visualizer.height - self.radius*2)
        
    def add_chunk(self, chunk):
        chunk.departure_position = self.get_departure_position(chunk)
        chunk.arrival_position = self.get_arrival_position(chunk)
        self.gatherer.add(chunk)

    def get_departure_position(self, chunk):
        if chunk.pan < 0.5:
            x = 0
        else:
            x = self.visualizer.width
        y = chunk.height * self.visualizer.height
        return Vector(x, y)

    def get_arrival_position(self, chunk):
        angle = 2 * math.pi * chunk.begin / chunk.file_length
        x = self.x + self.radius * math.cos(angle)
        y = self.y + self.radius * math.sin(angle)
        return Vector(x, y)
        
class Branches(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.files = {}
        self.peers = {}

    def InitGL(self):
        Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

        if not chunk.peer_id in self.peers:
            self.peers[chunk.peer_id] = Peer(chunk.departure_position, self)
        self.peers[chunk.peer_id].add_chunk(chunk)

    def render(self):
        self.draw_gathered_chunks()
        self.draw_branches()
 
    def draw_gathered_chunks(self):
        for f in self.files.values():
            for chunk in f.gatherer.pieces():
                self.draw_completed_piece(chunk, f)

    def draw_branches(self):
        for peer in self.peers.values():
            peer.draw()

    def draw_completed_piece(self, chunk, f):
        opacity = 0.3
        self.draw_sitting_piece(chunk, f, opacity)

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

run(Branches)
