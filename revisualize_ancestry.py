#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
from session import Session
from interpret import Interpreter
import math
import copy
import random
from sway import Sway

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *
import sys
from bezier import make_bezier
from ancestry_plotter import *
from vector import Vector2d
from smoother import Smoother

CURVE_PRECISION = 50
MARGIN = 20
LINE_WIDTH = 2.0 / 640
FORWARD = "forward"
BACKWARD = "backward"
NODE_CIRCLE_SIZE_PRECISION = 20
NODE_CIRCLE_GROWTH_TIME = 0.5
SUSTAIN_TIME = 5.0

class Ancestry(visualizer.Visualizer, AncestryPlotter):
    def __init__(self, tr_log, pieces, args):
        visualizer.Visualizer.__init__(self, args)
        AncestryPlotter.__init__(self, tr_log.total_file_size(), tr_log.lastchunktime(), args)

        if args.unfold == BACKWARD:
            for piece in pieces:
                self.add_piece(piece["id"], piece["t"], piece["begin"], piece["end"])
        elif args.unfold == FORWARD:
            self._remaining_pieces = copy.copy(pieces)

        self._autozoom = (args.geometry == CIRCLE and self.args.autozoom)
        if self._autozoom:
            self._max_pxy = 0
            self._zoom_smoother = Smoother()

        if args.node_style == CIRCLE:
            self._node_plot_method = self._draw_node_circle
            self._nodes = {}
        else:
            self._node_plot_method = None

    @staticmethod
    def add_parser_arguments(parser):
        AncestryPlotter.add_parser_arguments(parser)
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("-z", dest="timefactor", type=float, default=1.0)

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

        if self.args.node_style == CIRCLE:
            self._node_circle_lists = []
            for n in range(0, NODE_CIRCLE_SIZE_PRECISION):
                display_list = self.new_display_list_id()
                self._node_circle_lists.append(display_list)
                glNewList(display_list, GL_COMPILE)
                self._render_node_circle(0, 0, n)
                glEndList()

    def ReSizeGLScene(self, width, height):
        visualizer.Visualizer.ReSizeGLScene(self, width, height)
        self._size = min(width, height) - 2*MARGIN
        AncestryPlotter.set_size(self, self._size, self._size)

    def render(self):
        glTranslatef(MARGIN + (self.width - self._size)/2, MARGIN, 0)
        glLineWidth(LINE_WIDTH * self.width)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1,1,1)

        if self.args.unfold == BACKWARD:
            self._cursor_t = self._duration - self._adjusted_current_time() % self._duration
        elif self.args.unfold == FORWARD and len(self._remaining_pieces) > 0:
            piece = self._remaining_pieces[0]
            if self.args.ff or (piece["t"] <= self._adjusted_current_time()):
                self._remaining_pieces.pop(0)
                self.add_piece(piece["id"], piece["t"], piece["begin"], piece["end"])

        if self._autozoom:
            self._zoom = self._zoom_smoother.value()
            if self._zoom is None:
                self._zoom = 0.0
        else:
            self._zoom = 1.0

        self.plot()

        if self._autozoom:
            if self._max_pxy == 0:
                zoom = 0.5
            else:
                zoom = 0.5 + self._cursor_t/self._duration * 0.5 / self._max_pxy
            self._zoom_smoother.smooth(zoom, self.time_increment)

    def export_finished(self):
        return self._adjusted_current_time() >= (self._duration + SUSTAIN_TIME)

    def _adjusted_current_time(self):
        return self.current_time() * self.args.timefactor

    def _follow_piece(self, piece, child=None):
        self._update_and_draw_node(piece, piece.t, (piece.begin + piece.end) / 2)

        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                if self.args.unfold == FORWARD or self._cursor_t < older_version.t:
                    path.append((older_version.t,
                                 (older_version.begin + older_version.end) / 2))
            self.draw_path(piece, path)
            self._update_and_draw_node(piece, path[-1][0], path[-1][1])

        for parent in piece.parents.values():
            if self.args.unfold == FORWARD or self._cursor_t < parent.t:
                self._connect_generations(parent, piece, child)
                self._follow_piece(parent, piece)
            else:
                if self.args.unfold == BACKWARD:
                    t = self._cursor_t - pow(self._cursor_t - parent.t, 0.7)
                else:
                    t = self._cursor_t
                self._connect_generations(parent, piece, child, t)
                self._update_and_draw_node(parent, t, (parent.begin + parent.end) / 2)

    def _rect_position(self, t, byte_pos):
        x = float(byte_pos) / self._total_size * self._width
        y = (1 - t / self._duration) * self._height
        return Vector2d(x, y)

    def _circle_position(self, t, byte_pos):
        angle = float(byte_pos) / self._total_size * 2*math.pi
        rel_t = 1 - t / self._duration
        px = rel_t * math.cos(angle)
        py = rel_t * math.sin(angle)
        x = self._width / 2 + (px * self._zoom) * self._width / 2
        y = self._height / 2 + (py * self._zoom) * self._height / 2
        if self._autozoom:
            self._max_pxy = max([self._max_pxy, abs(px), abs(py)])
        return Vector2d(x, y)

    def draw_path(self, piece, points):
        glBegin(GL_LINE_STRIP)
        n = 0
        for (t, b) in points:
            x, y = self._position(t, b)
            if self.args.sway:
                a = 1 - float(n) / len(points)
                x += piece.sway.sway.x * a * self.width
                y += piece.sway.sway.y * a * self.height
                n += 1
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

    def _update_and_draw_node(self, piece, t, b):
        if self.args.sway:
            self._update_sway(piece)
        if self._node_plot_method:
            self._node_plot_method(piece, t, b)

    def _update_sway(self, piece):
        if not hasattr(piece, "sway"):
            piece.sway = Sway(self.args.sway_magnitude)
        piece.sway.update(self.time_increment)

    def _draw_node_circle(self, piece, t, b):
        try:
            appearance_time = piece.appearance_time
        except AttributeError:
            appearance_time = piece.appearance_time = self._adjusted_current_time()
        age = self._adjusted_current_time() - appearance_time
        if age > NODE_CIRCLE_GROWTH_TIME:
            size = NODE_CIRCLE_SIZE_PRECISION - 1
        else:
            size = int(pow(age / NODE_CIRCLE_GROWTH_TIME, 0.2) * (NODE_CIRCLE_SIZE_PRECISION-1))
        cx, cy = self._position(t, b)
        if self.args.sway:
            cx += piece.sway.sway.x * self.width
            cy += piece.sway.sway.y * self.height
        glPushMatrix()
        glTranslatef(cx, cy, 0)
        glCallList(self._node_circle_lists[size])
        glPopMatrix()

    def _render_node_circle(self, cx, cy, size):
        glColor3f(0,0,0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        angle = 0
        radius = self.args.node_size * self.width * size / (NODE_CIRCLE_SIZE_PRECISION-1)
        while angle < 2*math.pi:
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            glVertex2f(x, y)
            angle += 0.1
        x = cx + math.cos(0) * radius
        y = cy + math.sin(0) * radius
        glVertex2f(x, y)
        glEnd()

        glColor3f(1,1,1)
        glBegin(GL_LINE_STRIP)
        angle = 0
        while angle < 2*math.pi:
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            glVertex2f(x, y)
            angle += 0.1
        glEnd()

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--file", dest="selected_files", type=int, nargs="+")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-interpret", action="store_true")
parser.add_argument("-autozoom", action="store_true")
parser.add_argument("--unfold", choices=[FORWARD, BACKWARD], default=BACKWARD)
parser.add_argument("--node-style", choices=[CIRCLE])
parser.add_argument("--node-size", default=10.0/1000)
parser.add_argument("--fast-forward", action="store_true", dest="ff")
parser.add_argument("--sway", action="store_true")
parser.add_argument("--sway-magnitude", type=float, default=0.002)
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

if options.interpret:
    pieces = Interpreter().interpret(tr_log.chunks)
else:
    pieces = tr_log.chunks

Ancestry(tr_log, pieces, options).run()
