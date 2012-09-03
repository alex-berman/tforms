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
DURATION = 0.1

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
        self.playing_chunks = OrderedDict()
        self.gatherer = Gatherer()

    def add_chunk(self, chunk):
        self.playing_chunks[chunk.id] = chunk

    def update(self):
        outdated = filter(lambda chunk_id: self.playing_chunks[chunk_id].age() > DURATION,
                          self.playing_chunks)
        for chunk_id in outdated:
            self.gatherer.add(self.playing_chunks[chunk_id])
            del self.playing_chunks[chunk_id]

    def render(self):
        self.y = float(self.visualizer.height) / (self.visualizer.num_files + 1) * (
            self.filenum + 1)
        self.y1 = int(self.y - GATHERED_HEIGHT/2)
        self.y2 = int(self.y + GATHERED_HEIGHT/2)

        self.draw_background()
        self.draw_gathered_chunks()
        self.draw_playing_chunks()

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

    def draw_gathered_chunks(self):
        for chunk in self.gatherer.pieces():
            self.draw_gathered_chunk(chunk)

    def draw_playing_chunks(self):
        for chunk in self.playing_chunks.values():
            self.draw_playing_chunk(chunk)

    def draw_gathered_chunk(self, chunk):
        self.visualizer.set_color(GATHERED_COLOR)
        x1, x2 = self.chunk_position(chunk)
        glBegin(GL_QUADS)
        glVertex2i(x1, self.y2)
        glVertex2i(x2, self.y2)
        glVertex2i(x2, self.y1)
        glVertex2i(x1, self.y1)
        glEnd()

    def draw_playing_chunk(self, chunk):
        height = PLAYING_HEIGHT
        y1 = int(self.y - height/2)
        y2 = int(self.y + height/2)
        self.visualizer.set_color(PLAYING_COLOR)
        x1 = self.byte_to_px(chunk.begin)
        x2 = self.byte_to_px(chunk.end)
        x2 = max(x2, x1 + 1)
        glBegin(GL_QUADS)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def chunk_position(self, chunk):
        x1 = self.byte_to_px(chunk.begin)
        x2 = self.byte_to_px(chunk.end)
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
