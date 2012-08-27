import visualizer
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict

DURATION = 0.5
ARRIVAL_SIZE = 10
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05

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
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.min_byte = None
        self.max_byte = None
        self.x_ratio = None
        self.arriving_segments = OrderedDict()
        self.playing_segments = OrderedDict()
        self.gatherer = Gatherer()

    def add_segment(self, segment):
        segment.duration = DURATION
        if self.min_byte == None:
            self.min_byte = segment.begin
            self.max_byte = segment.end
        else:
            self.min_byte = min(self.min_byte, segment.begin)
            self.max_byte = max(self.max_byte, segment.end)
        self.arriving_segments[segment.id] = segment

    def play_segment(self, segment):
        pan = self.byte_to_coord(segment.begin)
        del self.arriving_segments[segment.id]
        self.playing_segments[segment.id] = segment

    def gather_segment(self, segment):
        del self.playing_segments[segment.id]
        self.gatherer.add(segment)

    def update_x_scope(self, time_increment):
        self._smoothed_min_byte.smooth(self.min_byte, time_increment)
        self._smoothed_max_byte.smooth(self.max_byte, time_increment)
        self.byte_offset = self._smoothed_min_byte.value()
        diff = self._smoothed_max_byte.value() - self._smoothed_min_byte.value()
        if diff == 0:
            self.x_ratio = 1
        else:
            self.x_ratio = 1.0 / diff

    def byte_to_coord(self, byte):
        return self.x_ratio * (byte - self.byte_offset)

class Puzzle(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()
        self.segments = {}

    def stopped_playing(self, segment_id, filenum):
        segment = self.segments[segment_id]
        self.files[filenum].gather_segment(segment)

    def render(self):
        if len(self.files) > 0:
            self.draw_segments()

    def draw_segments(self):
        self.update_y_scope()
        for f in self.files.values():
            self.update_segments(f)
            self.draw_file(f)

    def draw_file(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        f.update_x_scope(self.time_increment)
        self.draw_gathered_segments(f, y)
        self.draw_arriving_segments(f, y)
        self.draw_playing_segments(f, y)

    def draw_gathered_segments(self, f, y):
        for segment in f.gatherer.pieces():
            self.draw_segment(segment, 0, f, y)

    def update_segments(self, f):
        for segment in f.arriving_segments.values():
            age = self.now - segment.arrival_time
            if age > segment.duration:
                f.play_segment(segment)

    def draw_arriving_segments(self, f, y):
        for segment in f.arriving_segments.values():
            age = self.now - segment.arrival_time
            actuality = 1 - float(age) / segment.duration
            self.draw_segment(segment, actuality, f, y)

    def draw_playing_segments(self, f, y):
        for segment in f.playing_segments.values():
            self.draw_playing_segment(segment, f, y)
        
    def draw_segment(self, segment, actuality, f, y):
        y_offset = actuality * 10
        height = 3 + actuality * 10
        y1 = int(y + y_offset)
        y2 = int(y + y_offset + height)
        x1 = self.prepend_margin_width + int(f.byte_to_coord(segment.begin) * self.safe_width)
        x2 = self.prepend_margin_width + int(f.byte_to_coord(segment.end) * self.safe_width)
        x1, x2 = self.upscale(x1, x2, actuality)
        if x2 == x1:
            x2 = x1 + 1
        opacity = 0.2 + (actuality * 0.8)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()
        
    def draw_playing_segment(self, segment, f, y):
        y_offset = 0
        height = 3
        y1 = int(y + y_offset)
        y2 = int(y + y_offset + height)
        x1 = self.prepend_margin_width + int(f.byte_to_coord(segment.begin) * self.safe_width)
        x2 = self.prepend_margin_width + int(f.byte_to_coord(segment.end) * self.safe_width)
        if x2 == x1:
            x2 = x1 + 1
        glColor3f(1, 0, 0)
        glBegin(GL_QUADS)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def upscale(self, x1, x2, actuality):
        unscaled_size = x2 - x1
        desired_size = actuality * ARRIVAL_SIZE
        if desired_size > unscaled_size:
            mid = (x1 + x2) / 2
            half_desired_size = int(desired_size/2)
            x1 = mid - half_desired_size
            x2 = mid + half_desired_size
        return (x1, x2)

    def filenum_to_y_coord(self, filenum):
        return self.y_ratio * (filenum - self.filenum_offset + 1)

    def update_y_scope(self):
        min_filenum = min(self.files.keys())
        max_filenum = max(self.files.keys())
        self._smoothed_min_filenum.smooth(float(min_filenum), self.time_increment)
        self._smoothed_max_filenum.smooth(float(max_filenum), self.time_increment)
        self.filenum_offset = self._smoothed_min_filenum.value()
        diff = self._smoothed_max_filenum.value() - self._smoothed_min_filenum.value() + 1
        self.y_ratio = float(self.height) / (diff + 1)

if __name__ == '__main__':
    visualizer.run(Puzzle)
