from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector
import random
import math
from bezier import make_bezier
import colorsys

DURATION = 0.5
ARRIVAL_SIZE = 10
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05
MAX_BRANCH_AGE = 2.0
ARRIVED_HEIGHT = 3
MAX_HEIGHT = 13

class Branch:
    def __init__(self, filenum, file_length, peer):
        self.filenum = filenum
        self.file_length = file_length
        self.peer = peer
        self.visualizer = peer.visualizer
        self.f = self.visualizer.files[filenum]

    def set_cursor(self, cursor):
        self.cursor = cursor
        self.last_updated = time.time()

    def age(self):
        return self.visualizer.now - self.last_updated

    def target_position(self):
        x = self.f.byte_to_coord(self.cursor)
        y = self.visualizer.filenum_to_y_coord(self.filenum)
        if y > self.peer.departure_position.y:
            y -= 1
        else:
            y += ARRIVED_HEIGHT
        return Vector(x, y)

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
            branch = Branch(chunk.filenum, chunk.file_length, self)
            self.branches[self.branch_count] = branch
            self.branch_count += 1
        branch.set_cursor(chunk.end)

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
        self.update_branching_position()

    def update_branching_position(self):
        if len(self.branches) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([branch.target_position() for branch in self.branches.values()]) / \
                len(self.branches)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(new_branching_position, self.visualizer.time_increment)

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

    def reset(self):
        self._current_value = None

class File:
    def __init__(self, filenum, length, visualizer):
        self.filenum = filenum
        self.length = length
        self.visualizer = visualizer
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.min_byte = None
        self.max_byte = None
        self.x_ratio = None
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()

    def add_chunk(self, chunk):
        chunk.departure_position = self.get_departure_position(chunk)
        chunk.duration = DURATION
        if self.min_byte == None:
            self.min_byte = chunk.begin
            self.max_byte = chunk.end
        else:
            self.min_byte = min(self.min_byte, chunk.begin)
            self.max_byte = max(self.max_byte, chunk.end)
        self.arriving_chunks[chunk.id] = chunk

    def update_x_scope(self, time_increment):
        self._smoothed_min_byte.smooth(self.min_byte, time_increment)
        self._smoothed_max_byte.smooth(self.max_byte, time_increment)
        self.byte_offset = self._smoothed_min_byte.value()
        diff = self._smoothed_max_byte.value() - self._smoothed_min_byte.value()
        if diff == 0:
            self.x_ratio = 1
        else:
            self.x_ratio = 1.0 / diff

    def byte_to_coord(self, byte):
        # return self.visualizer.prepend_margin_width + \
        #     float(byte) / self.length * self.visualizer.safe_width
        return self.visualizer.prepend_margin_width + \
            (self.x_ratio * (byte - self.byte_offset)) * self.visualizer.safe_width

    def get_departure_position(self, chunk):
        if chunk.pan < 0.5:
            x = 0
        else:
            x = self.visualizer.width
        y = chunk.height * self.visualizer.height
        return Vector(x, y)

class Puzzle(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self.peers = {}
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.filenum, chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

    def render(self):
        if len(self.files) > 0:
            self.process_chunks()
            self.draw_chunks()
            self.draw_branches()

    def process_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                age = self.now - chunk.arrival_time
                if age > chunk.duration:
                    self.gather_chunk(chunk, f)

    def draw_branches(self):
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def draw_chunks(self):
        self.update_y_scope()
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        f.update_x_scope(self.time_increment)
        self.draw_gathered_chunks(f, y)
        self.draw_arriving_chunks(f, y)

    def draw_gathered_chunks(self, f, y):
        for chunk in f.gatherer.pieces():
            self.draw_chunk(chunk, 0, f, y)

    def draw_arriving_chunks(self, f, y):
        for chunk in f.arriving_chunks.values():
            age = self.now - chunk.arrival_time
            actuality = 1 - float(age) / chunk.duration
            #self.draw_arriving_chunk(chunk, actuality, f, y)

    def gather_chunk(self, chunk, f):
        if not chunk.peer_id in self.peers:
            self.peers[chunk.peer_id] = Peer(chunk.departure_position, self)
        self.peers[chunk.peer_id].add_chunk(chunk)
        del f.arriving_chunks[chunk.id]
        f.gatherer.add(chunk)

    def draw_chunk(self, chunk, actuality, f, y):
        zoom = self.get_zoom(actuality)
        y_offset = actuality * 10
        height = ARRIVED_HEIGHT + zoom * (MAX_HEIGHT - ARRIVED_HEIGHT)
        y1 = int(y + y_offset)
        y2 = int(y + y_offset + height)
        x1 = int(f.byte_to_coord(chunk.begin))
        x2 = int(f.byte_to_coord(chunk.end))
        x1, x2 = self.upscale(x1, x2, zoom)
        if x2 == x1:
            x2 = x1 + 1
        opacity = 0.2 + (zoom * 0.8)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def get_zoom(self, actuality):
        if actuality < .5:
            return actuality*2
        else:
            return (1-actuality)*2

    def upscale(self, x1, x2, zoom):
        unscaled_size = x2 - x1
        desired_size = zoom * ARRIVAL_SIZE
        if desired_size > unscaled_size:
            mid = (x1 + x2) / 2
            half_desired_size = int(desired_size/2)
            x1 = mid - half_desired_size
            x2 = mid + half_desired_size
        return (x1, x2)

    def filenum_to_y_coord(self, filenum):
        return self.y_ratio * (filenum - self.filenum_offset + 1)

    def update_y_scope(self):
        min_filenum = min(self.files.keys())
        max_filenum = max(self.files.keys())
        self._smoothed_min_filenum.smooth(float(min_filenum), self.time_increment)
        self._smoothed_max_filenum.smooth(float(max_filenum), self.time_increment)
        self.filenum_offset = self._smoothed_min_filenum.value()
        diff = self._smoothed_max_filenum.value() - self._smoothed_min_filenum.value() + 1
        self.y_ratio = float(self.height) / (diff + 1)

run(Puzzle)
