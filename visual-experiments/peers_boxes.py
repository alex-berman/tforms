from visualizer import Visualizer, run
from gatherer import Gatherer
import time
from OpenGL.GL import *
from collections import OrderedDict

MIN_SOUNDING_DURATION = 0.1
ARRIVAL_SIZE = 10
INNER_MARGIN = 0.1
GATHERED_HEIGHT = 20
DEPARTURE_HEIGHT = 3

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
    def __init__(self, filenum, length):
        self.filenum = filenum
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.x_ratio = 1.0 / length

    def add_chunk(self, chunk):
        sounding_duration = chunk.duration - chunk.fade_in
        if sounding_duration < MIN_SOUNDING_DURATION:
            chunk.duration += MIN_SOUNDING_DURATION - sounding_duration
        chunk.age = 0
        self.arriving_chunks[chunk.id] = chunk

    def byte_to_coord(self, byte):
        return self.x_ratio * byte

class Puzzle(Visualizer):
    def __init__(self, args):
        Visualizer.__init__(self, args)
        self.inner_margin_width = int(self.width * INNER_MARGIN)
        self.safe_width = self.width - self.inner_margin_width*2
        self.files = {}
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.filenum, chunk.file_length)
        self.files[chunk.filenum].add_chunk(chunk)

    def render(self):
        if len(self.files) > 0:
            self.draw_chunks()

    def draw_chunks(self):
        self.update_y_scope()
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        self.process_chunks(f)
        y = self.filenum_to_y_coord(f.filenum)
        self.draw_gathered_chunks(f, y)
        self.draw_arriving_chunks(f, y)

    def process_chunks(self, f):
        for chunk in f.arriving_chunks.values():
            chunk.age = self.now - chunk.arrival_time
            if chunk.age > chunk.duration:
                del f.arriving_chunks[chunk.id]
                f.gatherer.add(chunk)

    def draw_gathered_chunks(self, f, y):
        for chunk in f.gatherer.pieces():
            self.draw_completed_piece(chunk, f, y)

    def draw_arriving_chunks(self, f, y):
        for chunk in f.arriving_chunks.values():
            self.draw_chunk(chunk, f, y)

    def draw_chunk(self, chunk, f, y):
        if chunk.age < chunk.fade_in:
            self.draw_travelling_chunk(chunk, f, y)
        else:
            self.draw_sounding_chunk(chunk, f, y)

    def draw_travelling_chunk(self, chunk, f, destination_y):
        relative_age = chunk.age / chunk.fade_in
        height = DEPARTURE_HEIGHT + relative_age * (GATHERED_HEIGHT - DEPARTURE_HEIGHT)
        departure_y = chunk.height * self.height
        y = departure_y + (destination_y - departure_y) * relative_age
        y1 = int(y)
        y2 = int(y + height)
        if chunk.pan < 0.5:
            x1, x2 = self.position_from_left(chunk, relative_age, f)
        else:
            x1, x2 = self.position_from_right(chunk, relative_age, f)
        if x2 == x1:
            x2 = x1 + 1
        opacity = 0.2
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def draw_completed_piece(self, chunk, f, y):
        opacity = 0.2
        self.draw_sitting_piece(chunk, f, y, opacity)

    def draw_sounding_chunk(self, chunk, f, y):
        opacity = 1
        self.draw_sitting_piece(chunk, f, y, opacity)

    def draw_sitting_piece(self, chunk, f, y, opacity):
        height = GATHERED_HEIGHT
        y1 = int(y)
        y2 = int(y + height)
        x1 = self.inner_margin_width + int(f.byte_to_coord(chunk.begin) * self.safe_width)
        x2 = self.inner_margin_width + int(f.byte_to_coord(chunk.end) * self.safe_width)
        if x2 == x1:
            x2 = x1 + 1
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def position_from_left(self, chunk, relative_age, f):
        width = relative_age * ARRIVAL_SIZE
        departure_x1 = -width
        destination_x1 = self.inner_margin_width + f.byte_to_coord(chunk.begin) * self.safe_width
        x1 = departure_x1 + relative_age * (destination_x1 - departure_x1)
        x2 = x1 + width
        return (int(x1), int(x2))

    def position_from_right(self, chunk, relative_age, f):
        width = relative_age * ARRIVAL_SIZE
        departure_x1 = self.width
        destination_x1 = self.inner_margin_width + f.byte_to_coord(chunk.begin) * self.safe_width
        x1 = departure_x1 + relative_age * (destination_x1 - departure_x1)
        x2 = x1 + width
        return (int(x1), int(x2))

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
