from visualizer import Visualizer, run
import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
import math
import random
from vector import Vector, DirectionalVector
import colorsys
import time
from bezier import make_bezier

MAX_BRANCH_AGE = 2.0
CHUNK_SIZE_FACTOR = 0.000001
SOUNDING_CHUNK_SIZE_FACTOR = CHUNK_SIZE_FACTOR * 1.5
MAX_CHUNK_SIZE = 8.0 / 640
PASSIVE_COLOR = (0.9, 0.9, 0.9)
DECAY_TIME = 2.0
INNER_MARGIN = 100

class Smoother:
    RESPONSE_FACTOR = 0.01

    def __init__(self):
        self._current_value = None

    def smooth(self, new_value):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * \
                self.RESPONSE_FACTOR
        else:
            self._current_value = new_value

    def value(self):
        return self._current_value

    def reset(self):
        self._current_value = None

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
        return self.f.begin_position + (self.f.end_position - self.f.begin_position) * \
            self.cursor / self.file_length

class Peer:
    def __init__(self, departure_position, visualizer):
        self.departure_position = departure_position
        self.visualizer = visualizer
        self.smoothed_branching_position = Smoother()
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

    def find_branch(self, chunk):
        for branch in self.branches.values():
            if branch.filenum == chunk.filenum and branch.cursor == chunk.begin:
                return branch

    def update(self):
        self.delete_outdated_branches()
        self.update_branching_position()
        self.attract_files()

    def delete_outdated_branches(self):
        outdated = filter(lambda branch_id:
                              self.branches[branch_id].age() > MAX_BRANCH_AGE,
                          self.branches)
        for branch_id in outdated:
            del self.branches[branch_id]

    def update_branching_position(self):
        if len(self.branches) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([branch.target_position() for branch in self.branches.values()]) / \
                len(self.branches)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(new_branching_position)

    def attract_files(self):
        for branch in self.branches.values():
            self.attract_file(branch.f)

    def attract_file(self, f):
        distance = min((self.departure_position - f.begin_position).mag(),
                       (self.departure_position - f.end_position).mag())
        if distance > 100:
            midpoint = (f.begin_position + f.end_position) / 2
            f.begin_position += (self.departure_position - midpoint) * 0.001
            f.end_position += (self.departure_position - midpoint) * 0.001

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
        branching_position = self.smoothed_branching_position.value()
        for i in range(15):
            points.append(self.departure_position * (1-i/14.0)+
                          branching_position * i/14.0)
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
        self.begin_position = Vector(
            random.uniform(INNER_MARGIN, visualizer.width - INNER_MARGIN),
            random.uniform(INNER_MARGIN, visualizer.height - INNER_MARGIN))
        self.end_position = self.begin_position + DirectionalVector(
            random.uniform(0, 2*math.pi), 100)
        
    def add_chunk(self, chunk):
        chunk.departure_position = self.get_departure_position(chunk)
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
        #self.draw_files() # TEMP
        self.draw_gathered_chunks()
        self.draw_arriving_chunks()
        self.draw_branches()
 
    def draw_files(self): # TEMP
        glLineWidth(2.0)
        glColor3f(0.5,0.5,0.5)
        glBegin(GL_LINES)
        for f in self.files.values():
            glVertex2f(f.begin_position.x, f.begin_position.y)
            glVertex2f(f.end_position.x, f.end_position.y)
        glEnd()

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
        glLineWidth(4)
        self.set_completed_color(chunk)
        begin_position = self.completion_position(chunk, chunk.begin, f)
        end_position = self.completion_position(chunk, chunk.end, f)
        glBegin(GL_LINES)
        glVertex2f(begin_position.x, begin_position.y)
        glVertex2f(end_position.x, end_position.y)
        glEnd()

    def set_completed_color(self, chunk):
        age = self.now - chunk.last_updated
        if age > DECAY_TIME:
            relative_age = 1
        else:
            relative_age = age / DECAY_TIME

        active_color = colorsys.hsv_to_rgb(chunk.peer.hue, 0.35, 1)
        glColor3f(PASSIVE_COLOR[0] * relative_age + active_color[0] * (1-relative_age),
                  PASSIVE_COLOR[1] * relative_age + active_color[1] * (1-relative_age),
                  PASSIVE_COLOR[2] * relative_age + active_color[2] * (1-relative_age))

    def draw_sounding_chunk(self, chunk, f):
        size = chunk.byte_size * SOUNDING_CHUNK_SIZE_FACTOR * self.width
        mid_byte = (chunk.begin + chunk.end) / 2
        position = self.completion_position(chunk, mid_byte, f)
        chunk.peer.set_color(0.0)
        self.draw_point(position.x, position.y, size)

    def draw_point(self, x, y, size):
        size = min(size, MAX_CHUNK_SIZE * self.width)
        size = max(size, 1.0)
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    def completion_position(self, chunk, byte_position, f):
        return f.begin_position + (f.end_position - f.begin_position) * \
            byte_position / chunk.file_length

run(Branches)
