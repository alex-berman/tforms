import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from vector import Vector3d
from gatherer import Gatherer
from math_tools import sigmoid

WAVEFORM_SIZE = 60
WAVEFORM_MAGNITUDE = 30.0 / 480
#GATHERED_COLOR = Vector3d(0.6, 0.2, 0.1)
GATHERED_COLOR = Vector3d(0.3, 0.3, 0.3)
WAVEFORM_COLOR = Vector3d(1.0, 1.0, 1.0)
GATHERED_LINE_WIDTH = 1.0 / 480
WAVEFORM_LINE_WIDTH = 3.0 / 480
MAX_GRADIENT_HEIGHT = 3.0 / 480

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
            y = self.y + value * WAVEFORM_MAGNITUDE * self.visualizer.height
            glVertex2f(x, y)
            n += 1
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * sigmoid(pow(amp, 0.25))

    def amp_controlled_line_width(self, weak_line_width, strong_line_width, amp):
        return (weak_line_width + (strong_line_width - weak_line_width) * pow(amp, 0.25)) * self.visualizer.height

class File(visualizer.File):
    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.visualizer.playing_segments[segment.id] = segment

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
        self._gathered_segments_layer = self.new_layer(self._render_gathered_segments)

    def update(self):
        outdated = []
        for segment in self.playing_segments.values():
            if not segment.is_playing():
                self.gatherer.add(segment)
                outdated.append(segment.id)

        if len(outdated) > 0:
            for segment_id in outdated:
                del self.playing_segments[segment_id]
            self._gathered_segments_layer.refresh()

    def render(self):
        self.update()
        self._gathered_segments_layer.draw()
        self.draw_playing_segments()

    def draw_playing_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for segment in self.playing_segments.values():
            segment.render()

    def _render_gathered_segments(self):
        glBegin(GL_QUADS)
        x1 = 0
        x2 = self.width
        min_height = GATHERED_LINE_WIDTH * self.height
        for segment in self.gatherer.pieces():
            y1 = self.byte_to_py(segment.torrent_begin)
            y2 = max(self.byte_to_py(segment.torrent_end), y1 + min_height)
            if (y2 - y1) > min_height:
                d = min((y2 - y1) * 0.2, MAX_GRADIENT_HEIGHT * self.height)
                y1d = y1 + d
                y2d = y2 - d

                glColor3f(0, 0, 0)
                glVertex2f(x1, y1)

                glColor3f(*GATHERED_COLOR)
                glVertex2f(x1, y1d)
                glVertex2f(x2, y1d)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y1)



                glColor3f(0, 0, 0)
                glVertex2f(x1, y2)

                glColor3f(*GATHERED_COLOR)
                glVertex2f(x1, y2d)
                glVertex2f(x2, y2d)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y2)


                glColor3f(*GATHERED_COLOR)
                glVertex2f(x1, y1d)
                glVertex2f(x1, y2d)
                glVertex2f(x2, y2d)
                glVertex2f(x2, y1d)
            else:
                glColor3f(0, 0, 0)
                glVertex2f(x1, y1)

                glColor3f(*GATHERED_COLOR)
                glVertex2f(x1, y2)
                glVertex2f(x2, y2)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y1)
        glEnd()

    def byte_to_py(self, byte):
        return int(self.byte_to_relative_y(byte) * self.height)

    def byte_to_relative_y(self, byte):
        return float(byte) / self.torrent_length

    def handle_segment_waveform_value(self, segment, value):
        segment.waveform.appendleft(value)

visualizer.run(Waves)
