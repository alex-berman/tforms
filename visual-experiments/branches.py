from visualizer import Visualizer, run
import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
import math
import random
from boid import Boid
from vector import Vector
import colorsys
import time
from bezier import make_bezier

CIRCLE_PRECISION = 10
MAX_BRANCH_AGE = 2.0
CHUNK_SIZE_FACTOR = 0.000001
SOUNDING_CHUNK_SIZE_FACTOR = CHUNK_SIZE_FACTOR * 1.5
MAX_CHUNK_SIZE = 5.0 / 640

class Branch:
    def __init__(self, filenum, file_length, visualizer):
        self.filenum = filenum
        self.file_length = file_length
        self.visualizer = visualizer
        self.f = visualizer.files[filenum]

    def set_cursor(self, cursor):
        self.cursor = cursor
        self.last_updated = time.time()

    def age(self):
        return self.visualizer.now - self.last_updated

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
        self.branches = {}
        self.branch_count = 0
        self.hue = random.uniform(0, 1)

    def add_chunk(self, chunk):
        chunk.peer = self
        branch = self.find_branch(chunk)
        if not branch:
            branch = Branch(chunk.filenum, chunk.file_length, self.visualizer)
            self.branches[self.branch_count] = branch
            self.branch_count += 1
        branch.set_cursor(chunk.end)
        self.update_branching_position()

    def update_branching_position(self):
        average_target_position = \
            sum([branch.target_position() for branch in self.branches.values()]) / \
            len(self.branches)
        new_branching_position = self.departure_position*0.4 + average_target_position*0.6
        if self.branching_position == None:
            self.branching_position = new_branching_position
        else:
            self.branching_position += (new_branching_position - self.branching_position) * 0.1

    def find_branch(self, chunk):
        for branch in self.branches.values():
            if branch.filenum == chunk.filenum and branch.cursor == chunk.begin:
                return branch

    def update(self):
        outdated = filter(lambda branch_id:
                              self.branches[branch_id].age() > MAX_BRANCH_AGE,
                          self.branches)
        for branch_id in outdated:
            del self.branches[branch_id]

    def draw(self):
        if len(self.branches) > 0:
            glLineWidth(1.0)
            for branch in self.branches.values():
                relative_age = branch.age() / MAX_BRANCH_AGE
                self.set_color(relative_age)
                self.draw_curve(branch.target_position())

    def set_color(self, relative_age):
        color = colorsys.hsv_to_rgb(self.hue, 0.35, 1)
        glColor3f(relative_age + color[0] * (1-relative_age),
                  relative_age + color[1] * (1-relative_age),
                  relative_age + color[2] * (1-relative_age))

    def draw_line(self, p, q):
        glBegin(GL_LINES)
        glVertex2f(p.x, p.y)
        glVertex2f(q.x, q.y)
        glEnd()

    def draw_curve(self, target):
        points = []
        for i in range(5):
            points.append(self.departure_position * (1-i/4.0)+
                          self.branching_position * i/4.0)
        points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in points])
        points = bezier([t/50.0 for t in range(51)])
        glBegin(GL_LINE_STRIP)
        for x,y in points:
            glVertex2f(x, y)
        glEnd()

class Chunk(visualizer.Chunk):
    def joinable_with(self, other):
        return other.peer == self.peer

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.radius = 50.0
        self.x = random.uniform(self.radius, visualizer.width - self.radius*2)
        self.y = random.uniform(self.radius, visualizer.height - self.radius*2)
        
    def add_chunk(self, chunk):
        chunk.departure_position = self.get_departure_position(chunk)
        chunk.arrival_position = self.get_arrival_position(chunk)
        chunk.arrived = False
        self.arriving_chunks[chunk.id] = chunk

    def stopped_playing(self, chunk_id):
        chunk = self.arriving_chunks[chunk_id]
        del self.arriving_chunks[chunk_id]

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
        Visualizer.__init__(self, args, Chunk)
        self.files = {}
        self.peers = {}

    def InitGL(self):
        Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        self.play_chunk(chunk)

        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

        if not chunk.peer_id in self.peers:
            self.peers[chunk.peer_id] = Peer(chunk.departure_position, self)
        self.peers[chunk.peer_id].add_chunk(chunk)

        self.files[chunk.filenum].gatherer.add(chunk)

    def stopped_playing(self, chunk_id, filenum):
        self.files[filenum].stopped_playing(chunk_id)

    def render(self):
        self.draw_gathered_chunks()
        self.draw_arriving_chunks()
        self.draw_branches()
 
    def draw_gathered_chunks(self):
        for f in self.files.values():
            for chunk in f.gatherer.pieces():
                self.draw_completed_piece(chunk, f)

    def draw_arriving_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                self.draw_sounding_chunk(chunk, f)

    def draw_branches(self):
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def draw_completed_piece(self, chunk, f):
        self.draw_sitting_piece(chunk, f)

    def draw_sitting_piece(self, chunk, f):
        num_vertices = int(CIRCLE_PRECISION * float(chunk.end - chunk.begin) / chunk.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(4)
        chunk.peer.set_color(0.0)
        glBegin(GL_LINE_STRIP)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(i) / (num_vertices-1)
            x, y = self.completion_position(chunk, byte_position, f)
            glVertex2f(x, y)
        glEnd()

    def draw_sounding_chunk(self, chunk, f):
        size = chunk.byte_size * SOUNDING_CHUNK_SIZE_FACTOR * self.width
        mid_byte = (chunk.begin + chunk.end) / 2
        x, y = self.completion_position(chunk, mid_byte, f)
        chunk.peer.set_color(0.0)
        self.draw_point(x, y, size)

    def draw_point(self, x, y, size):
        size = min(size, MAX_CHUNK_SIZE * self.width)
        size = max(size, 1.0)
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    def completion_position(self, chunk, byte_position, f):
        angle = 2 * math.pi * byte_position / chunk.file_length
        x = f.x + f.radius * math.cos(angle)
        y = f.y + f.radius * math.sin(angle)
        return x, y

run(Branches)
