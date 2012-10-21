import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from dynamic_scope import DynamicScope
import random
from vector import Vector2d, Vector3d
from bezier import make_bezier
import colorsys

ARRIVAL_SIZE = 10
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05
ARRIVED_HEIGHT = 5
ARRIVED_OPACITY = 0.5
GREYSCALE = False
CONTROL_POINTS_BEFORE_BRANCH = 15
CURVE_PRECISION = 50
CURVE_OPACITY = 0.8
SEGMENT_DECAY_TIME = 1.0

class Segment(visualizer.Segment):
    def target_position(self):
        x = self.f.byte_to_coord(self.playback_byte_cursor())
        y = self.visualizer.filenum_to_y_coord(self.filenum) + ARRIVED_HEIGHT/2
        return Vector2d(x, y)

    def decay_time(self):
        return self.age() - self.duration

    def outdated(self):
        return (self.age() - self.duration) > SEGMENT_DECAY_TIME

    def draw_curve(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for x,y in self.curve():
            glVertex2f(x, y)
        glEnd()

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

    def draw_gathered(self):
        x1 = int(self.f.byte_to_coord(self.begin))
        x2 = int(self.f.byte_to_coord(self.end))
        self.draw_border(x1, x2)

    def draw_border(self, x1, x2):
        y = self.visualizer.filenum_to_y_coord(self.filenum)
        y1 = int(y)
        y2 = int(y + ARRIVED_HEIGHT)
        opacity = ARRIVED_OPACITY
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        if x2 == x1:
            x2 = x1 + 1

        glDisable(GL_LINE_SMOOTH)
        glDisable(GL_BLEND)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def draw_playing(self):
        if self.is_playing():
            trace_age = min(self.duration, 0.2)
            previous_byte_cursor = self.begin + min(self.age()-trace_age, 0) / \
                self.duration * self.byte_size
            if self.relative_age() < 1:
                opacity = 1
            else:
                opacity = 1 - pow((self.age() - self.duration) / SEGMENT_DECAY_TIME, .2)
            self.draw_playback_border()
            self.draw_gradient(previous_byte_cursor, self.playback_byte_cursor(), opacity)

    def draw_playback_border(self):
        x1 = int(self.f.byte_to_coord(self.begin))
        x2 = int(self.f.byte_to_coord(self.playback_byte_cursor()))
        self.draw_border(x1, x2)

    def draw_gradient(self, source, target, opacity):
        y = self.visualizer.filenum_to_y_coord(self.filenum)
        y1 = int(y)
        y2 = int(y + ARRIVED_HEIGHT) - 1
        if self.appending_to():
            x1 = int(self.f.byte_to_coord(self.appending_to().end)) - 1
        else:
            x1 = int(self.f.byte_to_coord(source)) + 1
        x2 = int(self.f.byte_to_coord(target)) - 1

        source_color = Vector3d(1, 1, 1)
        target_color = self.peer.color
        target_color += (source_color - target_color) * (1-opacity)

        glBegin(GL_QUADS)
        self.visualizer.set_color(source_color)
        glVertex2i(x1, y2)
        glVertex2i(x1, y1)
        self.visualizer.set_color(target_color)
        glVertex2i(x2, y1)
        glVertex2i(x2, y2)
        glEnd()

    def appending_to(self):
        if not hasattr(self, "_appending_to"):
            self._appending_to = self.f.gatherer.would_append(self)
        return self._appending_to


class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.departure_position = None
        self.smoothed_branching_position = Smoother()
        self.segments = {}
        hue = random.uniform(0, 1)
        self.color = Vector3d(*(colorsys.hsv_to_rgb(hue, 0.35, 1)))

    def add_segment(self, segment):
        if self.departure_position is None:
            self.departure_position = segment.departure_position
        segment.peer = self
        segment.gathered = False
        self.segments[segment.id] = segment

    def update(self):
        for segment in self.segments.values():
            if not segment.gathered and not segment.is_playing():
                segment.f.gatherer.add(segment)
                segment.gathered = True

        outdated = filter(lambda segment_id: self.segments[segment_id].outdated(),
                          self.segments)
        for segment_id in outdated:
            segment = self.segments[segment_id]
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
            for segment in self.segments.values():
                segment.draw_playing()
            for segment in self.segments.values():
                self.set_color(0)
                segment.draw_curve()

    def set_color(self, relative_age):
        if GREYSCALE:
            glColor3f(1 - CURVE_OPACITY,
                      1 - CURVE_OPACITY,
                      1 - CURVE_OPACITY)
        else:
            self.visualizer.set_color(self.color)

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

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.gatherer = Gatherer()
        self.x_scope = DynamicScope()

    def add_segment(self, segment):
        self.x_scope.put(segment.begin)
        self.x_scope.put(segment.end)
        segment.pan = (self.x_scope.map(segment.begin) + self.x_scope.map(segment.end)) / 2
        segment.departure_position = segment.peer_position()
        self.visualizer.playing_segment(segment, segment.pan)

    def render(self):
        self.x_scope.update()
        self.draw_gathered_segments()

    def draw_gathered_segments(self):
        for segment in self.gatherer.pieces():
            segment.draw_gathered()

    def byte_to_coord(self, byte):
        return self.visualizer.prepend_margin_width + \
            self.x_scope.map(byte) * self.visualizer.safe_width

class Puzzle(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer,
                                       segment_class=Segment)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self.segments = {}
        self.y_scope = DynamicScope(padding=1)

    def render(self):
        if len(self.files) > 0:
            self.y_scope.update()
            self.draw_gathered_segments()
            self.draw_branches()

    def draw_gathered_segments(self):
        for f in self.files.values():
            f.render()

    def draw_branches(self):
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def added_file(self, f):
        self.y_scope.put(f.filenum)

    def filenum_to_y_coord(self, filenum):
        return self.y_scope.map(filenum) * self.height

if __name__ == '__main__':
    visualizer.run(Puzzle)
