import rectangular_visualizer as visualizer
from OpenGL.GL import *
import sys
from bezier import make_bezier
from ancestry_plotter import AncestryPlotter
from vector import Vector2d

CURVE_PRECISION = 50
MARGIN = 20

class File(visualizer.File):
    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.visualizer.added_segment(segment)

class Ancestry(visualizer.Visualizer, AncestryPlotter):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self._initialized = False

    @staticmethod
    def add_parser_arguments(parser):
        AncestryPlotter.add_parser_arguments(parser)
        visualizer.Visualizer.add_parser_arguments(parser)

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._layer = self.new_layer(self._render_ancestry_layer)

    def resized_window(self):
        self._size = min(self.width, self.height) - 2*MARGIN
        AncestryPlotter.set_size(self, self._size, self._size)

    def added_segment(self, segment):
        AncestryPlotter.add_piece(self, segment.id, segment.t, segment.torrent_begin, segment.torrent_end)
        self._layer.refresh()

    def added_all_files(self):
        AncestryPlotter.__init__(self, self.total_size, self.download_duration, self.args)
        self._initialized = True

    def render(self):
        self._layer.draw()

    def _render_ancestry_layer(self):
        if self._initialized:
            glTranslatef(MARGIN + (self.width - self._size)/2, MARGIN, 0)
            glLineWidth(1)
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor3f(1,1,1)
            self.plot()

    def draw_path(self, points):
        glBegin(GL_LINE_STRIP)
        for (t, b) in points:
            x, y = self._position(t, b)
            glVertex2f(x, y)
        glEnd()

    def draw_curve(self, x1, y1, x2, y2):
        control_points = [
            Vector2d(x1, y1),
            Vector2d(x1 + (x2 - x1) * 0.3, y1),
            Vector2d(x1 + (x2 - x1) * 0.7, y2),
            Vector2d(x2, y2)
            ]
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        points = bezier(CURVE_PRECISION)
        glBegin(GL_LINE_STRIP)
        for x, y in points:
            glVertex2f(x, y)
        glEnd()

visualizer.run(Ancestry)
