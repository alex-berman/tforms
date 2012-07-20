from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict

MIN_DURATION = 0.1
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

class File:
    def __init__(self, filenum):
        self.filenum = filenum
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.min_byte = None
        self.max_byte = None
        self.x_ratio = None
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()

    def add_chunk(self, chunk):
        chunk.duration = max(chunk.duration, MIN_DURATION)
        if self.min_byte == None:
            self.min_byte = chunk.begin
            self.max_byte = chunk.end
        else:
            self.min_byte = min(self.min_byte, chunk.begin)
            self.max_byte = max(self.max_byte, chunk.end)
        self.arriving_chunks[chunk.id] = chunk

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

class Puzzle(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.filenum)
        self.files[chunk.filenum].add_chunk(chunk)

    def render(self):
        if len(self.files) > 0:
            self.draw_chunks()

    def draw_chunks(self):
        self.update_y_scope()
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        f.update_x_scope(self.time_increment)
        self.draw_gathered_chunks(f, y)
        self.draw_arriving_chunks(f, y)

    def draw_gathered_chunks(self, f, y):
        for chunk in f.gatherer.pieces():
            self.draw_chunk(chunk, 0, f, y)

    def draw_arriving_chunks(self, f, y):
        for chunk in f.arriving_chunks.values():
            age = self.now - chunk.arrival_time
            if age > chunk.duration:
                del f.arriving_chunks[chunk.id]
                f.gatherer.add(chunk)
            else:
                actuality = 1 - float(age) / chunk.duration
                self.draw_chunk(chunk, actuality, f, y)

    def draw_chunk(self, chunk, actuality, f, y):
        y_offset = actuality * 10
        height = 3 + actuality * 10
        y1 = int(y + y_offset)
        y2 = int(y + y_offset + height)
        x1 = self.prepend_margin_width + int(f.byte_to_coord(chunk.begin) * self.safe_width)
        x2 = self.prepend_margin_width + int(f.byte_to_coord(chunk.end) * self.safe_width)
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

run(Puzzle)
