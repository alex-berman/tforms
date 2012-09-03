import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from dynamic_scope import DynamicScope

ARRIVAL_SIZE = 10
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.playing_chunks = OrderedDict()
        self.gatherer = Gatherer()
        self.x_scope = DynamicScope()

    def add_chunk(self, chunk):
        self.x_scope.put(chunk.begin)
        self.x_scope.put(chunk.end)
        self.playing_chunks[chunk.id] = chunk

    def update(self):
        outdated = filter(lambda chunk_id: self.playing_chunks[chunk_id].relative_age() > 1,
                          self.playing_chunks)
        for chunk_id in outdated:
            self.gatherer.add(self.playing_chunks[chunk_id])
            del self.playing_chunks[chunk_id]
        self.x_scope.update()

    def render(self):
        self.y = self.visualizer.filenum_to_y_coord(self.filenum)
        self.draw_gathered_chunks()
        self.draw_playing_chunks()

    def draw_gathered_chunks(self):
        for chunk in self.gatherer.pieces():
            self.draw_chunk(chunk, 0)

    def draw_playing_chunks(self):
        for chunk in self.playing_chunks.values():
            self.draw_playing_chunk(chunk)

    def draw_playing_chunk(self, chunk):
        actuality = 1 - chunk.relative_age()
        self.draw_chunk(chunk, actuality)

    def draw_chunk(self, chunk, actuality):
        y_offset = actuality * 10
        height = 3 + actuality * 10
        y1 = int(self.y + y_offset)
        y2 = int(self.y + y_offset + height)
        x1 = self.visualizer.prepend_margin_width + \
            int(self.byte_to_coord(chunk.begin) * self.visualizer.safe_width)
        x2 = self.visualizer.prepend_margin_width + \
            int(self.byte_to_coord(chunk.end) * self.visualizer.safe_width)
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

    def byte_to_coord(self, byte):
        return self.x_scope.map(byte)

class Puzzle(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self.chunks = {}
        self.y_scope = DynamicScope(padding=1)

    def render(self):
        if len(self.files) > 0:
            self.y_scope.update()
            for f in self.files.values():
                f.update()
                f.render()

    def added_file(self, f):
        self.y_scope.put(f.filenum)

    def filenum_to_y_coord(self, filenum):
        return self.y_scope.map(filenum) * self.height

if __name__ == '__main__':
    visualizer.run(Puzzle)
