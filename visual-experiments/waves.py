import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from vector import Vector3d

WAVEFORM_SIZE = 60
WAVEFORM_MAGNITUDE = 30
MARGIN = 20
BACKGROUND_COLOR = Vector3d(1.0, 1.0, 1.0)
WAVEFORM_COLOR = Vector3d(0.0, 0.0, 0.0)

class Segment(visualizer.Segment):
    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0
        self.pan = .5
        self.y = self.f.byte_to_py(self.begin)

    def render(self):
        amp = max([abs(value) for value in self.waveform])
        self.visualizer.set_color(self.amp_controlled_color(
                BACKGROUND_COLOR, WAVEFORM_COLOR, amp))

        glBegin(GL_LINE_STRIP)
        n = 0
        for value in self.waveform:
            x = MARGIN + n * (self.visualizer.width - MARGIN) / WAVEFORM_SIZE
            y = self.y + value * WAVEFORM_MAGNITUDE
            glVertex2f(x, y)
            n += 1
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * pow(amp, 0.25)

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.playing_segments = collections.OrderedDict()

    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.playing_segments[segment.id] = segment

    def update(self):
        outdated = filter(lambda segment_id: self.playing_segments[segment_id].relative_age() > 1,
                          self.playing_segments)
        for segment_id in outdated:
            del self.playing_segments[segment_id]

    def render(self):
        self.draw_playing_segments()

    def draw_playing_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(1.0)
        for segment in self.playing_segments.values():
            segment.render()

    def byte_to_py(self, byte):
        return MARGIN + int(self.byte_to_relative_y(byte) * (self.visualizer.height - 2*MARGIN))

    def byte_to_relative_y(self, byte):
        return float(byte) / self.length

class Waves(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       segment_class=Segment)
        self.subscribe_to_waveform()

    def render(self):
        for f in self.files.values():
            f.update()
            f.render()

    def handle_segment_waveform_value(self, segment, value):
        segment.waveform.appendleft(value)

visualizer.run(Waves)
