import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector
import random
import math
from bezier import make_bezier
import colorsys
import copy

CIRCLE_PRECISION = 50
CIRCLE_THICKNESS = 10
ARRIVED_OPACITY = 0.5
GREYSCALE = True
RADIUS = 50
DAMPING = 0.95
CONTROL_POINTS_BEFORE_BRANCH = 15
CURVE_PRECISION = 50
CURVE_OPACITY = 0.8
SEGMENT_DECAY_TIME = 1.0

class Segment(visualizer.Segment):
    def target_position(self):
        return self.f.completion_position(
            float(self.end) / self.f.length,
            (self.f.inner_radius + self.f.radius) / 2)

    def is_playing(self):
        return self.relative_age() < 1

    def decay_time(self):
        return self.age() - self.duration

    def outdated(self):
        return (self.age() - self.duration) > SEGMENT_DECAY_TIME

    def draw_curve(self):
        glBegin(GL_LINE_STRIP)
        for x,y in self.curve():
            glVertex2f(x, y)
        glEnd()
        if self.is_playing():
            self.draw_cursor_line()

    def curve(self):
        control_points = []
        branching_position = self.peer.smoothed_branching_position.value()
        for i in range(CONTROL_POINTS_BEFORE_BRANCH):
            r = float(i) / (CONTROL_POINTS_BEFORE_BRANCH-1)
            control_points.append(self.peer.departure_position * (1-r) +
                                 branching_position * r)
        if self.is_playing():
            target = self.target_position()
        else:
            target = branching_position + (self.target_position() - branching_position) * \
                (1 - pow(self.decay_time(), 0.3))
        control_points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        return bezier(CURVE_PRECISION)

    def draw_cursor_line(self):
        relative_position = float(self.begin) / self.f.length
        self.draw_line(self.f.completion_position(relative_position, self.f.inner_radius),
                       self.f.completion_position(relative_position, self.f.radius))

    def draw_line(self, p, q):
        glBegin(GL_LINES)
        glVertex2f(p.x, p.y)
        glVertex2f(q.x, q.y)
        glEnd()

    def draw_playing(self):
        num_vertices = int(CIRCLE_PRECISION * float(self.end - self.begin) / self.byte_size)
        num_vertices = max(num_vertices, 2)
        glLineWidth(1)
        glBegin(GL_POLYGON)

        for i in range(num_vertices):
            byte_position = self.begin + self.byte_size * float(i) / (num_vertices-1)
            p = self.f.completion_position(byte_position / self.f.length, self.f.inner_radius)
            glColor3f(1,
                      float(num_vertices-i-1) / (num_vertices-1),
                      float(num_vertices-i-1) / (num_vertices-1)
                      )
            glVertex2f(p.x, p.y)
        for i in range(num_vertices):
            byte_position = self.begin + self.byte_size * float(num_vertices-i-1) / (num_vertices-1)
            p = self.f.completion_position(byte_position / self.f.length, self.f.radius)
            glColor3f(1,
                      float(i) / (num_vertices-1),
                      float(i) / (num_vertices-1)
                      )
            glVertex2f(p.x, p.y)

        glEnd()
            
class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.departure_position = None
        self.smoothed_branching_position = Smoother(5.0)
        self.segments = {}
        self.hue = random.uniform(0, 1)

    def add_segment(self, segment):
        if self.departure_position == None:
            self.departure_position = segment.departure_position
        segment.peer = self
        self.segments[segment.id] = segment

    def update(self):
        outdated = filter(lambda segment_id: self.segments[segment_id].outdated(),
                          self.segments)
        for segment_id in outdated:
            del self.segments[segment_id]
        self.update_branching_position()

    def update_branching_position(self):
        if len(self.segments) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([segment.target_position() for segment in self.segments.values()]) / \
                len(self.segments)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(
                new_branching_position, self.visualizer.time_increment)

    def draw(self):
        if len(self.segments) > 0:
            glLineWidth(1.0)
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            for segment in self.segments.values():
                segment.draw_playing()
            for segment in self.segments.values():
                self.set_color(0)
                segment.draw_curve()
            glDisable(GL_LINE_SMOOTH)
            glDisable(GL_BLEND)

    def set_color(self, relative_age):
        if GREYSCALE:
            glColor3f(1 - CURVE_OPACITY,
                      1 - CURVE_OPACITY,
                      1 - CURVE_OPACITY)
        else:
            color = colorsys.hsv_to_rgb(self.hue, 0.35, 1)
            glColor3f(relative_age + color[0] * (1-relative_age),
                      relative_age + color[1] * (1-relative_age),
                      relative_age + color[2] * (1-relative_age))

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

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.position = self.visualizer.place_new_circle()
        self.gatherer = Gatherer()
        self.inner_radius = self.visualizer.scale(RADIUS - CIRCLE_THICKNESS)
        self.radius = self.visualizer.scale(RADIUS)
        self.velocity = Vector(0,0)

    def add_segment(self, segment):
        pan = self.completion_position(
            float(segment.begin) / self.length, self.radius).x / self.visualizer.width
        segment.departure_position = segment.peer_position()
        self.gatherer.add(segment)

    def draw(self):
        glLineWidth(1)
        opacity = 0.5
        glColor3f(1-opacity, 1-opacity, 1-opacity)

        if self.completed():
            self.draw_completed_file()
        else:
            for segment in self.gatherer.pieces():
                self.draw_gathered_piece(segment)

    def completed(self):
        if len(self.gatherer.pieces()) == 1:
            piece = self.gatherer.pieces()[0]
            return piece.byte_size == self.length

    def draw_gathered_piece(self, segment):
        num_vertices = int(CIRCLE_PRECISION * float(segment.end - segment.begin) / segment.byte_size)
        num_vertices = max(num_vertices, 2)
        glBegin(GL_LINE_LOOP)

        for i in range(num_vertices):
            byte_position = segment.begin + segment.byte_size * float(i) / (num_vertices-1)
            p = self.completion_position(byte_position / self.length, self.inner_radius)
            glVertex2f(p.x, p.y)
        for i in range(num_vertices):
            byte_position = segment.begin + segment.byte_size * float(num_vertices-i-1) / (num_vertices-1)
            p = self.completion_position(byte_position / self.length, self.radius)
            glVertex2f(p.x, p.y)

        glEnd()

    def draw_completed_file(self):
        num_vertices = int(CIRCLE_PRECISION)

        glBegin(GL_LINE_LOOP)
        for i in range(num_vertices):
            byte_position = self.length * float(i) / (num_vertices-1)
            p = self.completion_position(byte_position / self.length, self.inner_radius)
            glVertex2f(p.x, p.y)
        glEnd()

        glBegin(GL_LINE_LOOP)
        for i in range(num_vertices):
            byte_position = self.length * float(i) / (num_vertices-1)
            p = self.completion_position(byte_position / self.length, self.radius)
            glVertex2f(p.x, p.y)
        glEnd()

    def completion_position(self, relative_position, radius):
        angle = 2 * math.pi * relative_position
        x = self.visualizer.x_offset + self.position.x + radius * math.cos(angle)
        y = self.visualizer.y_offset + self.position.y + radius * math.sin(angle)
        return Vector(x, y)

class Puzzle(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer,
                                       segment_class=Segment)
        self.x_offset = 0
        self.y_offset = 0
        self.x_offset_smoother = Smoother(.5)
        self.y_offset_smoother = Smoother(.5)
        self.segments = {}

    def render(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.draw_gathered_segments()
        self.draw_branches()
        glDisable(GL_LINE_SMOOTH)
        glDisable(GL_BLEND)

    def draw_gathered_segments(self):
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
        return Vector(random.uniform(self.scale(RADIUS), self.width - self.scale(RADIUS)),
                      random.uniform(self.scale(RADIUS), self.height - self.scale(RADIUS)))

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
            if f.filenum in [segment.filenum for segment in peer.segments.values()]:
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

    def scale(self, unscaled):
        return float(unscaled) / 640 * self.width

if __name__ == '__main__':
    visualizer.run(Puzzle)
