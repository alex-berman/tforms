#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
from session import Session

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *
import sys
from bezier import make_bezier
from ancestry_plotter import AncestryPlotter
from vector import Vector2d

CURVE_PRECISION = 50
MARGIN = 20

class Ancestry(visualizer.Visualizer, AncestryPlotter):
    def __init__(self, tr_log, args):
        visualizer.Visualizer.__init__(self, args)
        AncestryPlotter.__init__(self, tr_log.total_file_size(), tr_log.lastchunktime(), args)
        self.updated = False
        for chunk in tr_log.chunks:
            self.add_piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"])

    @staticmethod
    def add_parser_arguments(parser):
        AncestryPlotter.add_parser_arguments(parser)
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("-z", dest="timefactor", type=float, default=1.0)

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def ReSizeGLScene(self, width, height):
        visualizer.Visualizer.ReSizeGLScene(self, width, height)
        self._size = min(width, height) - 2*MARGIN
        AncestryPlotter.set_size(self, self._size, self._size)
        self.updated = False

    def render(self):
        glTranslatef(MARGIN + (self.width - self._size)/2, MARGIN, 0)
        glLineWidth(1)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1,1,1)
        self.min_t = self._duration - (self.current_time() * self.args.timefactor) % self._duration
        self.plot()
        self.updated = True

    def _follow_piece(self, piece):
        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                if older_version.t > self.min_t:
                    path.append((older_version.t,
                                 (older_version.begin + older_version.end) / 2))
            self.draw_path(path)

        for parent in piece.parents.values():
            if parent.t > self.min_t:
                self._connect_child_and_parent(
                    piece.t, (piece.begin + piece.end) / 2,
                    parent.t, (parent.begin + parent.end) / 2)
                self._follow_piece(parent)
            else:
                t = self.min_t - pow(self.min_t - parent.t, 0.7)
                self._connect_child_and_parent(
                    piece.t, (piece.begin + piece.end) / 2,
                    t, (parent.begin + parent.end) / 2)

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


parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--file", dest="selected_files", type=int, nargs="+")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
Ancestry.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

sessiondir = options.sessiondir
logfilename = "%s/session.log" % sessiondir

print "session: %s" % sessiondir

tr_log = TrLogReader(logfilename, options.torrentname,
                     realtime=False,
                     pretend_sequential=False).get_log()
if options.selected_files:
    tr_log.select_files(options.selected_files)
print >> sys.stderr, "found %d chunks" % len(tr_log.chunks)
tr_log.ignore_non_downloaded_files()

Ancestry(tr_log, options).run()
