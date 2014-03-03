#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
from session import Session
from interpret import Interpreter
import math
import copy
import random
from sway import Sway
from envelope import AdsrEnvelope

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
MARGIN = 0.03
FORWARD = "forward"
BACKWARD = "backward"
NODE_SIZE_PRECISION = 20
SUSTAIN_TIME = 10.0

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

        if args.node_size_envelope:
            attack, decay, sustain = args.node_size_envelope.split(",")
            self._node_size_envelope = AdsrEnvelope(
                attack, decay, sustain, args.node_size_envelope_slope)
        else:
            self._node_size_envelope = None

        if args.sway_envelope:
            attack, decay, sustain = args.sway_envelope.split(",")
            self._sway_envelope = AdsrEnvelope(attack, decay, sustain)
        else:
            self._sway_envelope = None


    @staticmethod
    def add_parser_arguments(parser):
        AncestryPlotter.add_parser_arguments(parser)
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("-z", dest="timefactor", type=float, default=1.0)

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

        if self.args.node_style == CIRCLE:
            self._node_circle_lists = {}

    def ReSizeGLScene(self, width, height):
        visualizer.Visualizer.ReSizeGLScene(self, width, height)
        self._margin = MARGIN * self.min_dimension
        self._size = self.min_dimension - 2*self._margin
        AncestryPlotter.set_size(self, self._size, self._size)

    def render(self):
        glTranslatef(self._margin + (self.width - self._size)/2, self._margin, 0)
        glLineWidth(self.args.line_width)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1,1,1)

        if self.args.unfold == BACKWARD:
            self._cursor_t = self._duration - self._adjusted_current_time() % self._duration
        elif self.args.unfold == FORWARD:
            if self.args.ff:
                self._add_oldest_remaining_piece()
            else:
                while (len(self._remaining_pieces) > 0 and
                       self._remaining_pieces[0]["t"] <= self._adjusted_current_time()):
                    self._add_oldest_remaining_piece()

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

    def _add_oldest_remaining_piece(self):
        piece = self._remaining_pieces.pop(0)
        self.add_piece(piece["id"], piece["t"], piece["begin"], piece["end"])

    def finished(self):
        return self.current_time() > (self._duration / self.args.timefactor + SUSTAIN_TIME)

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
        if self.args.sway:
            piece_sway_magnitude = self._sway_magnitude(piece)
        glBegin(GL_LINE_STRIP)
        n = 0
        for (t, b) in points:
            x, y = self._position(t, b)
            if self.args.sway:
                magnitude = (1 - float(n) / len(points)) * piece_sway_magnitude
                x += piece.sway.sway.x * magnitude * self._size
                y += piece.sway.sway.y * magnitude * self._size
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

    def draw_line(self, x1, y1, x2, y2):
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
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
        size = self._node_size(piece)
        cx, cy = self._position(t, b)
        if self.args.sway:
            piece_sway_magnitude = self._sway_magnitude(piece)
            cx += piece.sway.sway.x * piece_sway_magnitude * self._size
            cy += piece.sway.sway.y * piece_sway_magnitude * self._size
        self._render_node_circle(cx, cy, size)

    def _age(self, piece):
        try:
            appearance_time = piece.appearance_time
        except AttributeError:
            appearance_time = piece.appearance_time = self._adjusted_current_time()
        return self._adjusted_current_time() - appearance_time

    def _node_size(self, piece):
        if self.is_root_piece(piece):
            ancestry_factor = 3
        else:
            ancestry_factor = 1
        if self._node_size_envelope:
            age_factor = self._node_size_envelope.value(self._age(piece))
        else:
            age_factor = 1
        return int(min(ancestry_factor * age_factor, 1) * (NODE_SIZE_PRECISION-1))

    def _sway_magnitude(self, piece):
        age = self._age(piece)
        if self._sway_envelope:
            return self._sway_envelope.value(age)
        else:
            return 1

    def _render_node_circle(self, cx, cy, size):
        glPushMatrix()
        glTranslatef(cx, cy, 0)
        if size in self._node_circle_lists:
            glCallList(self._node_circle_lists[size])
        else:
            self._node_circle_lists[size] = self._create_and_execute_node_circle_list(size)
        glPopMatrix()

    def _create_and_execute_node_circle_list(self, size):
        display_list = self.new_display_list_id()
        glNewList(display_list, GL_COMPILE_AND_EXECUTE)
        glColor3f(1,1,1)
        glEnable(GL_POINT_SMOOTH)
        radius = max(self.args.node_size * self.width * size / (NODE_SIZE_PRECISION-1), 0.1)
        glPointSize(radius * 2)
        glBegin(GL_POINTS)
        glVertex2f(0, 0)
        glEnd()
        glEndList()
        return display_list

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--file", dest="selected_files", type=int, nargs="+")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-interpret", action="store_true")
parser.add_argument("-autozoom", action="store_true")
parser.add_argument("--unfold", choices=[FORWARD, BACKWARD], default=BACKWARD)
parser.add_argument("--node-style", choices=[CIRCLE])
parser.add_argument("--node-size-envelope", type=str,
                    help="attack-time,decay-time,sustain-level")
parser.add_argument("--node-size-envelope-slope", type=float, default=0.2)
parser.add_argument("--fast-forward", action="store_true", dest="ff")
parser.add_argument("--sway", action="store_true")
parser.add_argument("--sway-magnitude", type=float, default=0.002)
parser.add_argument("--sway-envelope", type=str,
                    help="attack-time,decay-time,sustain-level")
parser.add_argument("--line-width", type=float, default=2.0)
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

if options.interpret:
    pieces = Interpreter().interpret(tr_log.chunks)
else:
    pieces = tr_log.chunks

Ancestry(tr_log, pieces, options).run()
