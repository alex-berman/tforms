import rectangular_visualizer as visualizer
from OpenGL.GL import *
import sys
from bezier import make_bezier
from ancestry_plotter import AncestryPlotter
from vector import Vector2d

CURVE_PRECISION = 50
MARGIN = 20

class File(visualizer.File):
    def add_chunk(self, chunk):
        self.visualizer.add_chunk(chunk)

class Ancestry(visualizer.Visualizer, AncestryPlotter):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self.updated = False
        self.list = 1

    @staticmethod
    def add_parser_arguments(parser):
        AncestryPlotter.add_parser_arguments(parser)

    def ReSizeGLScene(self, width, height):
        visualizer.Visualizer.ReSizeGLScene(self, width, height)
        self._size = min(width, height) - 2*MARGIN
        AncestryPlotter.set_size(self, self._size, self._size)

    def add_chunk(self, chunk):
        AncestryPlotter.add_piece(self, chunk.id, chunk.t, chunk.torrent_begin, chunk.torrent_end)
        self.updated = False

    def added_all_files(self):
        AncestryPlotter.__init__(self, self.torrent_length, self.download_duration, self.args)

    def render(self):
        if self.updated:
            self.draw()
        else:
            self.update_and_draw()

    def update_and_draw(self):
        glNewList(self.list, GL_COMPILE_AND_EXECUTE)
        glTranslatef(MARGIN + (self.width - self._size)/2, MARGIN, 0)
        glLineWidth(1)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(0,0,0)
        self.plot()
        glEndList()
        self.updated = True

    def draw(self):
        glCallList(self.list)

    def draw_path(self, points):
        glBegin(GL_LINE_STRIP)
        for (t, b) in points:
            x, y = self._position(t, b)
            glVertex2f(x, y)
        glEnd()

    def draw_curve(self, points):
        glBegin(GL_LINE_STRIP)
        for x, y in points:
            glVertex2f(x, y)
        glEnd()

    def _connect_child_and_parent(self, t1, b1, t2, b2):
        x1, y1 = self._position(t1, b1)
        x2, y2 = self._position(t2, b2)
        curve = self._curve(x1, y1, x2, y2)
        self.draw_curve(curve)

    def _curve(self, x1, y1, x2, y2):
        control_points = [
            Vector2d(x1, y1),
            Vector2d(x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.35),
            Vector2d(x1 + (x2 - x1) * 0.55, y1 + (y2 - y1) * 0.65),
            Vector2d(x2, y2)
            ]
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        return bezier(CURVE_PRECISION)

visualizer.run(Ancestry)
