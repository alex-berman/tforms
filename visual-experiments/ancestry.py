import rectangular_visualizer as visualizer
from OpenGL.GL import *
import sys
from bezier import make_bezier
from ancestry_tracker import AncestryTracker, Piece
from vector import Vector2d

CURVE_PRECISION = 50

class File(visualizer.File):
    def add_chunk(self, chunk):
        self.visualizer.add_chunk(chunk)

class Ancestry(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self.ancestry_tracker = AncestryTracker()
        self.chunks = []
        self.updated = False
        self.list = 1

    def add_chunk(self, chunk):
        chunk.parents = {}
        chunk.growth = []
        self.ancestry_tracker.add(Piece(chunk.id, chunk.t, chunk.torrent_begin, chunk.torrent_end))
        self.chunks.append(chunk)
        self.updated = False

    def render(self):
        if self.updated:
            self.draw()
        else:
            self.update_and_draw()

    def update_and_draw(self):
        glNewList(self.list, GL_COMPILE_AND_EXECUTE)
        self._override_recursion_limit()
        glLineWidth(1)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(0,0,0)
        for piece in self.ancestry_tracker.last_pieces():
            self._follow_piece(piece)
        glEndList()
        self.updated = True

    def draw(self):
        glCallList(self.list)

    def _follow_piece(self, piece):
        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                path.append((older_version.t,
                             (older_version.begin + older_version.end) / 2))
            self._draw_path(path)

        for parent in piece.parents.values():
            self._connect_child_and_parent(
                piece.t, (piece.begin + piece.end) / 2,
                parent.t, (parent.begin + parent.end) / 2)
            self._follow_piece(parent)

    def _draw_path(self, points):
        glBegin(GL_LINE_STRIP)
        for (t, b) in points:
            x, y = self._position(t, b)
            glVertex2f(x, y)
        glEnd()

    def _draw_curve(self, points):
        glBegin(GL_LINE_STRIP)
        for x, y in points:
            glVertex2f(x, y)
        glEnd()

    def _position(self, t, byte_pos):
        x = t / self.download_duration * self.width
        y = float(byte_pos) / self.torrent_length * self.height
        return x, y

    def _connect_child_and_parent(self, t1, b1, t2, b2):
        x1, y1 = self._position(t1, b1)
        x2, y2 = self._position(t2, b2)
        curve = self._curve(x1, y1, x2, y2)
        self._draw_curve(curve)

    def _curve(self, x1, y1, x2, y2):
        control_points = [
            Vector2d(x1, y1),
            Vector2d(x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.35),
            Vector2d(x1 + (x2 - x1) * 0.55, y1 + (y2 - y1) * 0.65),
            Vector2d(x2, y2)
            ]
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        return bezier(CURVE_PRECISION)

    def _override_recursion_limit(self):
        sys.setrecursionlimit(max(len(self.chunks), sys.getrecursionlimit()))

visualizer.run(Ancestry)
