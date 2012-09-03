import visualizer
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector3d

MARGIN = 20
GATHERED_HEIGHT = 10
PLAYING_HEIGHT = 10
BACKGROUND_COLOR = Vector3d(.9, .9, .9)
GATHERED_COLOR = Vector3d(.7, .9, .7)
PLAYING_COLOR = Vector3d(1, 0, 0)

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
        pan = (float(segment.begin) + float(segment.end))/2 / self.length
        self.visualizer.playing_segment(segment, pan)
        self.playing_segments[segment.id] = segment

    def update(self):
        outdated = filter(lambda segment_id: self.playing_segments[segment_id].relative_age() > 1,
                          self.playing_segments)
        for segment_id in outdated:
            self.gatherer.add(self.playing_segments[segment_id])
            del self.playing_segments[segment_id]

    def render(self):
        self.y = float(self.visualizer.height) / (self.visualizer.num_files + 1) * (
            self.filenum + 1)
        self.y1 = int(self.y - GATHERED_HEIGHT/2)
        self.y2 = int(self.y + GATHERED_HEIGHT/2)

        self.draw_background()
        self.draw_gathered_segments()
        self.draw_playing_segments()

    def draw_background(self):
        x1 = self.byte_to_px(0)
        x2 = self.byte_to_px(self.length)
        self.visualizer.set_color(BACKGROUND_COLOR)
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
        self.visualizer.set_color(GATHERED_COLOR)
        x1, x2 = self.segment_position(segment)
        glBegin(GL_QUADS)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def draw_playing_segment(self, segment):
        trace_age = 0.5
        previous_byte_cursor = segment.begin + max(segment.age()-trace_age, 0) / \
                segment.duration * segment.byte_size
        height = PLAYING_HEIGHT
        y1 = int(self.y - height/2)
        y2 = int(self.y + height/2)
        x0 = self.byte_to_px(segment.begin)
        x1 = self.byte_to_px(previous_byte_cursor)
        x3 = self.byte_to_px(segment.playback_byte_cursor())
        x3 = max(x3, x1 + 1)
        x2 = (x1 + x3) / 2

        self.visualizer.set_color(GATHERED_COLOR)
        glBegin(GL_QUADS)
        glVertex2i(x0, y1)
        glVertex2i(x0, y2)
        glVertex2i(x1, y2)
        glVertex2i(x1, y1)
        glEnd()

        glBegin(GL_QUADS)
        self.visualizer.set_color(GATHERED_COLOR)
        glVertex2i(x1, y2)
        glVertex2i(x1, y1)
        self.visualizer.set_color(PLAYING_COLOR)
        glVertex2i(x2, y1)
        glVertex2i(x2, y2)
        glEnd()

        glBegin(GL_QUADS)
        self.visualizer.set_color(PLAYING_COLOR)
        glVertex2i(x2, y1)
        glVertex2i(x2, y2)
        self.visualizer.set_color(GATHERED_COLOR)
        glVertex2i(x3, y2)
        glVertex2i(x3, y1)
        glEnd()

    def segment_position(self, segment):
        x1 = self.byte_to_px(segment.begin)
        x2 = self.byte_to_px(segment.end)
        x2 = max(x2, x1 + 1)
        return x1, x2

    def byte_to_px(self, byte):
        return MARGIN + int(
            float((self.visualizer.max_file_length - self.length) / 2 + byte) / \
            self.visualizer.max_file_length * (self.visualizer.width - 2*MARGIN))

class Simple(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)

    def added_file(self, _f):
        self.max_file_length = max([f.length for f in self.files.values()])

    def render(self):
        for f in self.files.values():
            f.update()
            f.render()

visualizer.run(Simple)
