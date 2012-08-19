import visualizer
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict

MARGIN = 20

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

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.playing_segments = OrderedDict()
        self.gatherer = Gatherer()

    def add_segment(self, segment):
        self.playing_segments[segment.id] = segment

    def update(self):
        outdated = filter(lambda segment_id: self.playing_segments[segment_id].relative_age() > 1,
                          self.playing_segments)
        for segment_id in outdated:
            del self.playing_segments[segment_id]

    def render(self):
        height = 3
        y = float(self.visualizer.height) / (self.visualizer.num_files + 1) * (self.filenum + 1)
        self.y1 = int(y)
        self.y2 = int(y + height)

        self.draw_background()
        self.draw_gathered_segments()
        self.draw_playing_segments()

    def draw_background(self):
        height = 3
        x1 = MARGIN
        x2 = self.visualizer.width - MARGIN
        glColor3f(0.8, 0.8, 0.9)
        glBegin(GL_QUADS)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def draw_gathered_segments(self):
        for segment in self.gatherer.pieces():
            self.draw_gathered_segment(segment)

    def draw_playing_segments(self):
        for segment in self.playing_segments.values():
            self.draw_playing_segment(segment)

    def draw_gathered_segment(self, segment):
        opacity = 0.2
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        x1, x2 = self.segment_position(segment)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def draw_playing_segment(self, segment):
        glColor3f(1, 0, 0)
        x1, x2 = self.segment_position(segment)
        glBegin(GL_QUADS)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def segment_position(self, segment):
        x1 = self.byte_to_px(segment.begin)
        x2 = self.byte_to_px(segment.end)
        if x2 == x1:
            x2 = x1 + 1
        return x1, x2

    def byte_to_px(self, byte):
        return MARGIN + int(float(byte) / self.length * (self.visualizer.width - 2*MARGIN))

class Simple(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self.files = {}

    def render(self):
        for f in self.files.values():
            f.update()
            f.render()

visualizer.run(Simple)
