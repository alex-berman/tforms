import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from vector import Vector3d
from gatherer import Gatherer

WAVEFORM_SIZE = 60
WAVEFORM_MAGNITUDE = 30
MARGIN = 0.2
GATHERED_COLOR = Vector3d(0.9, 0.9, 0.9)
OUTLINE_COLOR = Vector3d(0.9, 0.9, 0.9)
WAVEFORM_COLOR = Vector3d(0.0, 0.0, 0.0)

class Segment(visualizer.Segment):
    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0
        self.pan = 0.5

    def render(self):
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
        self.playing_segments = collections.OrderedDict()
        self.gatherer = Gatherer()

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
        self.draw_outline()
        self.draw_gathered_segments()
        self.draw_playing_segments()

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

    def draw_playing_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(1.0)
        for segment in self.playing_segments.values():
            segment.render()

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
        segment.waveform.appendleft(value)

    def ReSizeGLScene(self, *args):
        visualizer.Visualizer.ReSizeGLScene(self, *args)
        margin = MARGIN * min(self.width, self.height)
        self.x1 = margin
        self.y1 = margin
        self.x2 = self.width-margin
        self.y2 = self.height-margin

visualizer.run(Waves)
