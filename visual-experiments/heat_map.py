#!/usr/bin/python

from argparse import ArgumentParser
import collections
import math

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from vector import Vector2d
from OpenGL.GL import *
from math_tools import sigmoid
from title_renderer import TitleRenderer

sys.path.append("geo")
import locations

MARKER_PRECISION = 20
MAX_FADE_TIME = 0.3

def clamp(value, min_value, max_value):
    return max(min(max_value, value), min_value)

class Location(Vector2d):
    def __init__(self, x_y_tuple):
        x, y = x_y_tuple
        Vector2d.__init__(self, x, y)

class File(visualizer.File):
    def add_segment(self, segment):
        #self.visualizer.playing_segment(segment) # TEMP
        location = self.visualizer.peers_by_addr[segment.peer.addr].location
        if location:
            self.visualizer.added_segment(segment)

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.arrival_time = self.visualizer.current_time()
        self.visualizer.added_peer(self)

class Segment(visualizer.Segment):
    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self._fade_time = min(self.duration/2, MAX_FADE_TIME)

    def relative_size(self):
        age = self.age()
        if age < self._fade_time:
            return sigmoid(age / self._fade_time)
        elif age > (self.duration - self._fade_time):
            return 1 - sigmoid(1 - (self.duration - age) / self._fade_time)
        else:
            return 1

class HeatMap(visualizer.Visualizer):
    def __init__(self, args):
        self._history_layer = None
        self._load_locations()
        visualizer.Visualizer.__init__(
            self, args, file_class=File, peer_class=Peer, segment_class=Segment)
        self._set_horizontal_scope()
        self._set_verical_scope()
        self._map_margin = self.parse_margin_argument(self.args.map_margin)
        if self.args.continents:
            import world
            self._world = world.World(1.0, 1.0)

    def _set_horizontal_scope(self):
        self._hscope_min, self._hscope_max = map(float, self.args.hscope.split(":"))
        self._hscope_size = self._hscope_max - self._hscope_min

    def _set_verical_scope(self):
        self._vscope_min, self._vscope_max = map(float, self.args.vscope.split(":"))
        self._vscope_size = self._vscope_max - self._vscope_min
        
    @staticmethod
    def add_parser_arguments(parser):
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("--disable-title", action="store_true")
        parser.add_argument("--test-title", type=str)
        parser.add_argument("--hscope", type=str, default="0:1")
        parser.add_argument("--vscope", type=str, default="0:1")
        parser.add_argument("--continents", action="store_true")
        visualizer.Visualizer.add_margin_argument(parser, "--map-margin")

    def reset(self):
        visualizer.Visualizer.reset(self)
        self.playing_segments = collections.OrderedDict()
        self._first_segment_received = False
        self._title_renderer = None

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._history_layer = self.new_layer(self._render_history)

    def resized_window(self):
        self._map_margin.update()
        self._map_width = self.width - self._map_margin.left - self._map_margin.right
        self._map_height = self.height - self._map_margin.top - self._map_margin.bottom
        self._size_factor = (float(self._map_width) + self._map_height) / 2 / ((1024 + 768) / 2)

        self._marker_lists = []
        for n in range(0, MARKER_PRECISION):
            display_list = self.new_display_list_id()
            self._marker_lists.append(display_list)
            glNewList(display_list, GL_COMPILE)
            self._render_marker_circle(n)
            glEndList()

    def configure_2d_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.window_width, 0.0, self.window_height, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)

    def _load_locations(self):
        self._locations = collections.defaultdict(int)
        for location in locations.get_locations():
            self._add_location(location)
        self._max_frequency = max(self._locations.values())

    def _add_location(self, location):
        if not location:
            return
        self._locations[Location(location)] += 1
        if self._history_layer:
            self._history_layer.refresh()

    def added_segment(self, segment):
        self._first_segment_received = True
        self.playing_segments[segment.id] = segment

    def added_peer(self, peer):
        self._add_location(peer.location)

    def render(self):
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._update()
        if self.args.continents:
            self._render_continents()
        else:
            self._history_layer.draw()
        self._render_activity()

        if not self.args.disable_title:
            if not self._title_renderer and (self._first_segment_received or self.args.test_title):
                self._create_title_renderer()
            if self._title_renderer:
                self._render_title()

    def _render_continents(self):
        glColor4f(0.8,0.8,0.8,1)
        glLineWidth(1.0)
        for path in self._world.paths:
            self._draw_path(path)

    def _draw_path(self, path):
        glBegin(GL_LINE_STRIP)
        for x, y in path:
            self._location_vertex(x, y)
        glEnd()

    def _create_title_renderer(self):
        if self.args.test_title:
            title = self.args.test_title
        else:
            title = self.torrent_title
        size = 30.0 * self._size_factor
        self._title_renderer = TitleRenderer(title, size, self)

    def _render_title(self):
        glColor3f(1,1,1)
        x = self._map_margin.left + 10.0 / 640 * self.width
        y = self.height * 0.03
        self._title_renderer.render(x, y)

    def _render_history(self):
        glColor4f(0.8,0.8,0.8,1)
        for location, frequency in self._locations.iteritems():
            point_size = pow(float(frequency) / self._max_frequency, 0.15) * 4 * self._size_factor
            #point_size = max(point_size, 3)
            glPointSize(point_size)
            glBegin(GL_POINTS)
            self._location_vertex(location.x, location.y)
            glEnd()

    def _location_vertex(self, location_x, location_y):
        p = Vector2d(
            (location_x - self._hscope_min) / self._hscope_size,
            (location_y - self._vscope_min) / self._vscope_size)
        glVertex2f(
            self._map_margin.left + p.x * self._map_width,
            self._map_margin.bottom + (1-p.y) * self._map_height)

    def _render_activity(self):
        glColor4f(1,1,1,1)
        for segment in self.playing_segments.values():
            location = self.peers_by_addr[segment.peer.addr].location
            x, y = location

            # #n = int(MARKER_PRECISION * (((self.now - segment.peer.arrival_time) * 0.8))) % MARKER_PRECISION
            # n = clamp(int(segment.relative_size() * MARKER_PRECISION), 0, MARKER_PRECISION-1)
            # glPushMatrix()
            # glTranslatef(x * self.width, y * self.height, 0)
            # #self._render_marker_circle(n)
            # glCallList(self._marker_lists[n])
            # glPopMatrix()

            #size = (1.0 + 0.3 * math.sin((self.now - segment.peer.arrival_time) * 2.0)) * 8 / 640
            #glPointSize(size * self.width)
            glPointSize(max(int(segment.relative_size() * 10.0 * self._size_factor), 1))
            glBegin(GL_POINTS)
            self._location_vertex(x, y)
            glEnd()

    def _render_marker_circle(self, n):
        # t = float(n) / MARKER_PRECISION * 2*math.pi
        # radius = (1.0 + 0.15 * math.sin(t)) * 8 / 640

        stroke_radius = float(n) / MARKER_PRECISION * 8 / 640
        shadow_inner_radius = float(n) / MARKER_PRECISION * 4 / 640
        shadow_outer_radius = float(n) / MARKER_PRECISION * 12 / 640

        glColor4f(0,0,0,0.5)
        glBegin(GL_QUADS)
        for i in range(20):
            a1 = float(i) / 20 * 2*math.pi
            a2 = float(i+1) / 20 * 2*math.pi
            x1 = shadow_outer_radius * math.cos(a1) * self.min_dimension
            y1 = shadow_outer_radius * math.sin(a1) * self.min_dimension
            x2 = shadow_inner_radius * math.cos(a1) * self.min_dimension
            y2 = shadow_inner_radius * math.sin(a1) * self.min_dimension
            x3 = shadow_inner_radius * math.cos(a2) * self.min_dimension
            y3 = shadow_inner_radius * math.sin(a2) * self.min_dimension
            x4 = shadow_outer_radius * math.cos(a2) * self.min_dimension
            y4 = shadow_outer_radius * math.sin(a2) * self.min_dimension
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)
            glVertex2f(x3, y3)
            glVertex2f(x4, y4)
        glEnd()

        glColor4f(1,1,1,1)
        glLineWidth(2.0 * self._size_factor)
        glBegin(GL_LINE_LOOP)
        for i in range(20):
            a = float(i) / 20 * 2*math.pi
            cx = stroke_radius * math.cos(a) * self.min_dimension
            cy = stroke_radius * math.sin(a) * self.min_dimension
            glVertex2f(cx, cy)
        glEnd()

    def _update(self):
        self._delete_outdated_segments()

    def _delete_outdated_segments(self):
        outdated = []
        for segment in self.playing_segments.values():
            if not segment.is_playing():
                outdated.append(segment.id)

        for segment_id in outdated:
            del self.playing_segments[segment_id]

if __name__ == "__main__":
    parser = ArgumentParser()
    HeatMap.add_parser_arguments(parser)
    options = parser.parse_args()
    HeatMap(options).run()
