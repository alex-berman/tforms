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
import copy

DURATION = 0.5
CIRCLE_PRECISION = 50
CIRCLE_THICKNESS = 10
MAX_BRANCH_AGE = 2.0
BRANCH_SUSTAIN = 1.5
ARRIVED_OPACITY = 0.5
GREYSCALE = True
RADIUS = 50.0
DAMPING = 0.95

class Branch:
    def __init__(self, filenum, file_length, peer):
        self.filenum = filenum
        self.file_length = file_length
        self.peer = peer
        self.visualizer = peer.visualizer
        self.f = self.visualizer.files[filenum]
        self.playing_chunks = OrderedDict()

    def add_chunk(self, chunk):
        self.playing_chunks[chunk.id] = chunk
        self.cursor = chunk.end
        self.last_updated = time.time()
        self.last_chunk = chunk

    def age(self):
        return self.visualizer.now - self.last_updated

    def target_position(self):
        return self.f.completion_position(self.last_chunk, self.last_chunk.begin,
                                          (self.f.inner_radius + self.f.radius) / 2)

    def update(self):
        for chunk in self.playing_chunks.values():
            age = self.visualizer.now - chunk.arrival_time
            if age > chunk.duration:
                del self.playing_chunks[chunk.id]

    def draw_playing_chunks(self):
        if len(self.playing_chunks) > 0:
            chunks_list = list(self.playing_chunks.values())
            chunk = copy.copy(chunks_list[0])
            chunk.end = chunks_list[-1].end
            chunk.byte_size = chunk.end - chunk.begin
            self.f.draw_playing_chunk(chunk)
            
class Peer:
    def __init__(self, departure_position, visualizer):
        self.departure_position = departure_position
        self.visualizer = visualizer
        self.smoothed_branching_position = Smoother(5.0)
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
        branch.add_chunk(chunk)

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

        for branch in self.branches.values():
            branch.update()

    def update_branching_position(self):
        if len(self.branches) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([branch.target_position() for branch in self.branches.values()]) / \
                len(self.branches)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(
                new_branching_position, self.visualizer.time_increment)

    def draw(self):
        if len(self.branches) > 0:
            glLineWidth(1.0)
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            for branch in self.branches.values():
                branch.draw_playing_chunks()
            for branch in self.branches.values():
                self.set_color(0)
                self.draw_curve(branch)
            glDisable(GL_LINE_SMOOTH)
            glDisable(GL_BLEND)

    def set_color(self, relative_age):
        if GREYSCALE:
            glColor3f(0,0,0)
        else:
            color = colorsys.hsv_to_rgb(self.hue, 0.35, 1)
            glColor3f(relative_age + color[0] * (1-relative_age),
                      relative_age + color[1] * (1-relative_age),
                      relative_age + color[2] * (1-relative_age))

    def draw_line(self, p, q):
        glBegin(GL_LINES)
        glVertex2f(p.x, p.y)
        glVertex2f(q.x, q.y)
        glEnd()

    def draw_curve(self, branch):
        points = []
        branching_position = self.smoothed_branching_position.value()
        for i in range(15):
            points.append(self.departure_position * (1-i/14.0)+
                          branching_position * i/14.0)
        if branch.age() < BRANCH_SUSTAIN:
            target = branch.target_position()
        else:
            target = branching_position + (branch.target_position() - branching_position) * \
                (1 - (branch.age() - BRANCH_SUSTAIN) / (MAX_BRANCH_AGE - BRANCH_SUSTAIN))
        points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in points])
        points = bezier([t/50.0 for t in range(51)])
        glBegin(GL_LINE_STRIP)
        for x,y in points:
            glVertex2f(x, y)
        glEnd()
        if branch.age() < BRANCH_SUSTAIN:
            last_chunk = branch.last_chunk
            f = self.visualizer.files[last_chunk.filenum]
            self.draw_line(f.completion_position(last_chunk, last_chunk.begin, f.inner_radius),
                           f.completion_position(last_chunk, last_chunk.begin, f.radius))

class Smoother:
    def __init__(self, response_factor):
        self._response_factor = response_factor
        self._current_value = None

    def smooth(self, new_value, time_increment):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * \
                self._response_factor * time_increment
        else:
            self._current_value = new_value
        return self._current_value

    def value(self):
        return self._current_value

    def reset(self):
        self._current_value = None

class File:
    def __init__(self, filenum, length, visualizer, position, radius):
        self.filenum = filenum
        self.length = length
        self.visualizer = visualizer
        self.position = position
        self.gatherer = Gatherer()
        self.inner_radius = radius - CIRCLE_THICKNESS
        self.radius = radius
        self.velocity = Vector(0,0)

    def add_chunk(self, chunk):
        chunk.departure_position = self.get_departure_position(chunk)
        chunk.duration = DURATION
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
            p = self.completion_position(chunk, byte_position, self.inner_radius)
            glVertex2f(p.x, p.y)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(num_vertices-i-1) / (num_vertices-1)
            p = self.completion_position(chunk, byte_position, self.radius)
            glVertex2f(p.x, p.y)

        glEnd()

    def draw_playing_chunk(self, chunk):
        num_vertices = int(CIRCLE_PRECISION * float(chunk.end - chunk.begin) / chunk.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(1)
        glBegin(GL_POLYGON)

        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(i) / (num_vertices-1)
            p = self.completion_position(chunk, byte_position, self.inner_radius)
            glColor3f(1,
                      float(num_vertices-i-1) / (num_vertices-1),
                      float(num_vertices-i-1) / (num_vertices-1)
                      )
            glVertex2f(p.x, p.y)
        for i in range(num_vertices):
            byte_position = chunk.begin + chunk.byte_size * float(num_vertices-i-1) / (num_vertices-1)
            p = self.completion_position(chunk, byte_position, self.radius)
            glColor3f(1,
                      float(i) / (num_vertices-1),
                      float(i) / (num_vertices-1)
                      )
            glVertex2f(p.x, p.y)

        glEnd()

    def completion_position(self, chunk, byte_position, radius):
        angle = 2 * math.pi * byte_position / chunk.file_length
        x = self.visualizer.x_offset + self.position.x + radius * math.cos(angle)
        y = self.visualizer.y_offset + self.position.y + radius * math.sin(angle)
        return Vector(x, y)

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
        self.files = {}
        self.peers = {}
        self.x_offset = 0
        self.y_offset = 0
        self.x_offset_smoother = Smoother(.5)
        self.y_offset_smoother = Smoother(.5)

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = self.new_file(chunk.filenum, chunk.file_length)
        self.files[chunk.filenum].add_chunk(chunk)

        if not chunk.peer_id in self.peers:
            self.peers[chunk.peer_id] = Peer(chunk.departure_position, self)
        self.peers[chunk.peer_id].add_chunk(chunk)

        self.play_chunk(chunk)

    def new_file(self, filenum, file_length):
        position = self.place_new_circle()
        return File(filenum, file_length, self, position, RADIUS)

    def render(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.draw_gathered_chunks()
        self.draw_branches()
        glDisable(GL_LINE_SMOOTH)
        glDisable(GL_BLEND)

    def draw_gathered_chunks(self):
        for f in self.files.values():
            f.velocity = (f.velocity + self.repositioning_force(f)) * DAMPING
            f.velocity.limit(3.0)
        for f in self.files.values():
            f.position += f.velocity
            f.draw()
        self.center()

    def center(self):
        if len(self.files) > 0:
            new_x_offset = self.width / 2 - (min([f.position.x for f in self.files.values()]) +
                                             max([f.position.x for f in self.files.values()])) / 2
            new_y_offset = self.height / 2 - (min([f.position.y for f in self.files.values()]) +
                                              max([f.position.y for f in self.files.values()])) / 2
            self.x_offset = self.x_offset_smoother.smooth(new_x_offset, self.time_increment)
            self.y_offset = self.y_offset_smoother.smooth(new_y_offset, self.time_increment)

    def draw_branches(self):
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def place_new_circle(self):
        return self.random_position()

    def random_position(self):
        return Vector(random.uniform(RADIUS, self.width - RADIUS),
                      random.uniform(RADIUS, self.height - RADIUS))

    def repositioning_force(self, f):
        f.force = Vector(0,0)
        self.repel_from_and_attract_to_other_files(f)
        self.attract_to_peers(f)
        return f.force

    def repel_from_and_attract_to_other_files(self, f):
        for other in self.files.values():
            if other != f:
                self.apply_coulomb_repulsion(f, other.position)
                self.apply_hooke_attraction(f, other.position)

    def attract_to_peers(self, f):
        for peer in self.peers.values():
            if f.filenum in [branch.filenum for branch in peer.branches.values()]:
                self.attract_to_peer(f, peer)

    def attract_to_peer(self, f, peer):
        self.apply_hooke_attraction(f, peer.departure_position)

    def apply_coulomb_repulsion(self, f, other):
        d = f.position - other
        distance = d.mag()
        if distance == 0:
            f.force += Vector(random.uniform(0.0, 0.1),
                              random.uniform(0.0, 0.1))
        else:
            d.normalize()
            f.force += d / pow(distance, 2) * 1000

    def apply_hooke_attraction(self, f, other):
        d = other - f.position
        f.force += d * 0.0001

if __name__ == '__main__':
    run(Puzzle)
