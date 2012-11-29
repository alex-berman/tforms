import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from vector import Vector2d, Vector3d
from gatherer import Gatherer
from bezier import make_bezier
from smoother import Smoother
import random
import math

WAVEFORM_SIZE = 60
WAVEFORM_FRAMES_TO_FILE = 10
WAVEFORM_MAGNITUDE = 30
FILE_MARGIN_X = 0.3
FILE_MARGIN_Y = 0.1
CURVE_MARGIN_Y = 0.3
GATHERED_COLOR = Vector3d(0.9, 0.9, 0.9)
OUTLINE_COLOR = Vector3d(0.9, 0.9, 0.9)
WAVEFORM_COLOR = Vector3d(0.0, 0.0, 0.0)

CONTROL_POINTS_BEFORE_BRANCH = 15
CURVE_PRECISION_TO_FILE = 50
RELATIVE_BRANCHING_POSITION = .4

class Segment(visualizer.Segment):
    HALF_PI = math.pi/2

    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0
        self.pan = 0.5

    def add_to_waveform(self, value):
        if self.peer.rightward:
            self.waveform.appendleft(value)
        else:
            self.waveform.append(value)

    def target_position(self):
        return self.branch_file_crossing()

    def outdated(self):
        return not self.is_playing()

    def branch_file_crossing(self):
        y = self.visualizer.byte_to_py(self.torrent_begin)
        if self.peer.rightward:
            x = self.visualizer.x1
        else:
            x = self.visualizer.x2
        return Vector2d(x, y)

    def draw_playing(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(1.0)

        self.draw_waveform_to_file()
        self.draw_waveform_in_file()

    def draw_waveform_to_file(self):
        curve = self.curve_to_file()
        curve = self._stretch_curve_with_waveform(curve)
        glBegin(GL_LINE_STRIP)
        for x,y in curve:
            glVertex2f(x, y)
        glEnd()

    def curve_to_file(self):
        control_points = []
        branching_position = self.peer.smoothed_branching_position.value()
        for i in range(CONTROL_POINTS_BEFORE_BRANCH):
            r = float(i) / (CONTROL_POINTS_BEFORE_BRANCH-1)
            control_points.append(self.peer.departure_position * (1-r) +
                                 branching_position * r)
        target = self.branch_file_crossing()
        control_points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        return bezier(CURVE_PRECISION_TO_FILE)

    def _stretch_curve_with_waveform(self, curve):
        vertex_for_waveform_start = self._vertex_for_waveform_start(curve)
        num_waveform_vertices = CURVE_PRECISION_TO_FILE - vertex_for_waveform_start
        result = curve[0:vertex_for_waveform_start]
        for n in range(num_waveform_vertices):
            relative_n = float(n) / num_waveform_vertices
            x1, y1 = curve[vertex_for_waveform_start + n - 1]
            x2, y2 = curve[vertex_for_waveform_start + n]
            bearing = math.atan2(y2 - y1, x2 - x1)
            stretch_angle = bearing + self.HALF_PI
            w = self.waveform[
                int(relative_n * WAVEFORM_FRAMES_TO_FILE)]
            stretch = w * WAVEFORM_MAGNITUDE * relative_n
            v = (x2 + stretch * math.cos(stretch_angle),
                 y2 + stretch * math.sin(stretch_angle))
            result.append(v)
        return result

    def _vertex_for_waveform_start(self, curve):
        result = 0
        length = 0
        for n in range(CURVE_PRECISION_TO_FILE - 1):
            x1, y1 = curve[n]
            x2, y2 = curve[n+1]
            dx = x2 - x1
            dy = y2 - y1
            length += math.sqrt(dx*dx + dy*dy)
            if length > self.visualizer.waveform_length_to_file:
                return result
            result += 1
        return result

    def draw_waveform_in_file(self):
        amp = max([abs(value) for value in self.waveform])
        self.visualizer.set_color(self.amp_controlled_color(
                GATHERED_COLOR, WAVEFORM_COLOR, amp))

        glBegin(GL_LINE_STRIP)
        n = 0
        y_offset = self.visualizer.byte_to_py(self.torrent_begin)
        for value in self.waveform:
            x = self.visualizer.x1 + n * (self.visualizer.x2 - self.visualizer.x1) / (WAVEFORM_SIZE-1)
            y = y_offset + value * WAVEFORM_MAGNITUDE
            glVertex2f(x, y)
            n += 1
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * pow(amp, 0.25)

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.departure_position = None
        self.smoothed_branching_position = Smoother()
        self.segments = {}
        self.rightward = random.choice([True, False])
        if self.rightward:
            x = 0
        else:
            x = self.visualizer.width
        self.position = Vector2d(
            x,
            CURVE_MARGIN_Y * self.visualizer.height + \
                random.uniform(0, (1-CURVE_MARGIN_Y*2) * self.visualizer.height))

    def add_segment(self, segment):
        if self.departure_position is None:
            self.departure_position = segment.departure_position
        segment.peer = self
        segment.gathered = False
        self.segments[segment.id] = segment

    def update(self):
        for segment in self.segments.values():
            if not segment.gathered and not segment.is_playing():
                self.visualizer.gather(segment)
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
            new_branching_position = self.departure_position * RELATIVE_BRANCHING_POSITION \
                + average_target_position * (1-RELATIVE_BRANCHING_POSITION)
            self.smoothed_branching_position.smooth(
                new_branching_position, self.visualizer.time_increment)

    def draw(self):
        if len(self.segments) > 0:
            for segment in self.segments.values():
                segment.draw_playing()

class File(visualizer.File):
    def add_segment(self, segment):
        segment.departure_position = segment.peer.position
        self.visualizer.playing_segment(segment)
        self.visualizer.playing_segments[segment.id] = segment
        segment.gathered = False


class Waves(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer,
                                       segment_class=Segment)
        self.subscribe_to_waveform()
        self.playing_segments = collections.OrderedDict()
        self.gatherer = Gatherer()

    def gather(self, segment):
        self.gatherer.add(segment)

    def render(self):
        #self.draw_outline()
        self.draw_gathered_segments()
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def draw_outline(self):
        glDisable(GL_LINE_SMOOTH)
        glLineWidth(1.0)
        glColor3f(*OUTLINE_COLOR)
        glBegin(GL_LINE_STRIP)
        glVertex2f(self.x1, self.y1)
        glVertex2f(self.x1, self.y2)
        glVertex2f(self.x2, self.y2)
        glVertex2f(self.x2, self.y1)
        glVertex2f(self.x1, self.y1)
        glEnd()

    def draw_gathered_segments(self):
        glColor3f(*GATHERED_COLOR)
        glBegin(GL_QUADS)
        for segment in self.gatherer.pieces():
            y1 = self.byte_to_py(segment.torrent_begin)
            y2 = self.byte_to_py(segment.torrent_end)
            if y2 == y1:
                y2 += 1
            glVertex2f(self.x1, y1)
            glVertex2f(self.x1, y2)
            glVertex2f(self.x2, y2)
            glVertex2f(self.x2, y1)
        glEnd()

    def byte_to_py(self, byte):
        return self.y1 + int(self.byte_to_relative_y(byte) * (self.y2 - self.y1))

    def byte_to_relative_y(self, byte):
        return float(byte) / self.torrent_length

    def handle_segment_waveform_value(self, segment, value):
        segment.add_to_waveform(value)

    def ReSizeGLScene(self, *args):
        visualizer.Visualizer.ReSizeGLScene(self, *args)
        margin_x = FILE_MARGIN_X * self.width
        margin_y = FILE_MARGIN_Y * self.height
        self.x1 = margin_x
        self.y1 = margin_y
        self.x2 = self.width - margin_x
        self.y2 = self.height - margin_y
        self.waveform_length_to_file = margin_x
        self.waveform_length_in_file = self.x2 - self.x1

visualizer.run(Waves)
