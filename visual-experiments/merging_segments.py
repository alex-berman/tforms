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
        self.playing_segments = OrderedDict()
        self.gatherer = Gatherer()
        self.x_scope = DynamicScope()

    def add_segment(self, segment):
        self.x_scope.put(segment.begin)
        self.x_scope.put(segment.end)
        pan = (self.byte_to_coord(segment.begin) + self.byte_to_coord(segment.end)) / 2
        self.visualizer.playing_segment(segment, pan)
        self.playing_segments[segment.id] = segment

    def update(self):
        outdated = filter(lambda segment_id: self.playing_segments[segment_id].relative_age() > 1,
                          self.playing_segments)
        for segment_id in outdated:
            self.gatherer.add(self.playing_segments[segment_id])
            del self.playing_segments[segment_id]
        self.x_scope.update()

    def render(self):
        self.y = self.visualizer.filenum_to_y_coord(self.filenum)
        self.draw_gathered_segments()
        self.draw_playing_segments()

    def draw_gathered_segments(self):
        for segment in self.gatherer.pieces():
            self.draw_segment(segment, 0)

    def draw_playing_segments(self):
        for segment in self.playing_segments.values():
            self.draw_playing_segment(segment)

    def draw_playing_segment(self, segment):
        actuality = 1 - segment.relative_age()
        self.draw_segment(segment, actuality)

    def draw_segment(self, segment, actuality):
        y_offset = actuality * 10
        height = 3 + actuality * 10
        y1 = int(self.y + y_offset)
        y2 = int(self.y + y_offset + height)
        x1 = self.visualizer.prepend_margin_width + \
            int(self.byte_to_coord(segment.begin) * self.visualizer.safe_width)
        x2 = self.visualizer.prepend_margin_width + \
            int(self.byte_to_coord(segment.end) * self.visualizer.safe_width)
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
        self.segments = {}
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
