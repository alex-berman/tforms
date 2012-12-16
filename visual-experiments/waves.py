import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from vector import Vector3d
from gatherer import Gatherer

WAVEFORM_SIZE = 60
WAVEFORM_MAGNITUDE = 30
GATHERED_COLOR = Vector3d(0.4, 0.4, 0.4)
WAVEFORM_COLOR = Vector3d(1.0, 1.0, 1.0)
GATHERED_LINE_WIDTH = 2.0
WAVEFORM_LINE_WIDTH = 3.0

class Segment(visualizer.Segment):
    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0
        self.pan = 0.5
        self.y = self.visualizer.byte_to_py(self.torrent_begin)

    def render(self):
        amp = max([abs(value) for value in self.waveform])
        glLineWidth(self.amp_controlled_line_width(
                GATHERED_LINE_WIDTH, WAVEFORM_LINE_WIDTH, amp))
        self.visualizer.set_color(self.amp_controlled_color(
                GATHERED_COLOR, WAVEFORM_COLOR, amp))

        glBegin(GL_LINE_STRIP)
        n = 0
        for value in self.waveform:
            x = n * self.visualizer.width / (WAVEFORM_SIZE-1)
            y = self.y + value * WAVEFORM_MAGNITUDE
            glVertex2f(x, y)
            n += 1
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * pow(amp, 0.25)

    def amp_controlled_line_width(self, weak_line_width, strong_line_width, amp):
        return weak_line_width + (strong_line_width - weak_line_width)

class File(visualizer.File):
    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.visualizer.playing_segments[segment.id] = segment
        segment.gathered = False

class Waves(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       segment_class=Segment)
        self.subscribe_to_waveform()

    def reset(self):
        visualizer.Visualizer.reset(self)
        self.playing_segments = collections.OrderedDict()
        self.gatherer = Gatherer()

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def update(self):
        for segment in self.playing_segments.values():
            if not segment.gathered and not segment.is_playing():
                self.gatherer.add(segment)
                segment.gathered = True

        outdated = filter(lambda segment_id: self.playing_segments[segment_id].relative_age() > 1,
                          self.playing_segments)
        for segment_id in outdated:
            del self.playing_segments[segment_id]

    def render(self):
        self.update()
        self.draw_gathered_segments()
        self.draw_playing_segments()

    def draw_playing_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for segment in self.playing_segments.values():
            segment.render()

    def draw_gathered_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glColor3f(*GATHERED_COLOR)
        glBegin(GL_QUADS)
        x1 = 0
        x2 = self.width
        for segment in self.gatherer.pieces():
            y1 = self.byte_to_py(segment.torrent_begin)
            y2 = max(self.byte_to_py(segment.torrent_end), y1 + GATHERED_LINE_WIDTH)
            glVertex2f(x1, y1)
            glVertex2f(x1, y2)
            glVertex2f(x2, y2)
            glVertex2f(x2, y1)
        glEnd()

    def byte_to_py(self, byte):
        return int(self.byte_to_relative_y(byte) * self.height)

    def byte_to_relative_y(self, byte):
        return float(byte) / self.torrent_length

    def handle_segment_waveform_value(self, segment, value):
        segment.waveform.appendleft(value)

visualizer.run(Waves)
