import visualizer
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector3d

MARGIN = 20
HEIGHT = 10
BACKGROUND_COLOR = Vector3d(.9, .9, .9)
GATHERED_COLOR = Vector3d(.7, .9, .7)
PLAYING_COLOR = Vector3d(1, 0, 0)
FADE_IN = 0.005
FADE_OUT = 0.006

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
        y = float(self.visualizer.height) / (self.visualizer.num_files + 1) * (self.filenum + 1)
        self.y1 = int(y - HEIGHT/2)
        self.y2 = int(y + HEIGHT/2)

        self.draw_background()
        self.draw_gathered_segments()
        self.draw_playing_segments()

    def draw_background(self):
        height = 3
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
        self.visualizer.set_color(self.playing_color(segment))
        x1 = self.byte_to_px(segment.begin)
        x2 = self.byte_to_px(segment.begin + segment.byte_size * segment.relative_age())
        x2 = max(x2, x1 + 1)
        glBegin(GL_QUADS)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def playing_color(self, segment):
        if segment.relative_age() < FADE_IN:
            return BACKGROUND_COLOR + (PLAYING_COLOR - BACKGROUND_COLOR) * (
                segment.relative_age() / FADE_IN)
        elif (1 - segment.relative_age() < FADE_OUT):
            return GATHERED_COLOR + (PLAYING_COLOR - GATHERED_COLOR) * (
                (1 - segment.relative_age()) / FADE_OUT)
        else:
            return PLAYING_COLOR

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
