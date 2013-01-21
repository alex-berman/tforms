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

    def reset(self):
        visualizer.Visualizer.reset(self)
        self.playing_segments = collections.OrderedDict()
        self._first_segment_received = False

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._history_layer = self.new_layer(self._render_history)

    def ReSizeGLScene(self, *args):
        visualizer.Visualizer.ReSizeGLScene(self, *args)
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
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._update()
        self._history_layer.draw()
        self._render_activity()
        if self._first_segment_received:
            self._render_title()

    def _render_title(self):
        glColor3f(1,1,1)
        glLineWidth(1.0)
        glPointSize(1.0)
        self.draw_text(
            text = self.torrent_title.upper(),
            scale = 0.2 / 1024 * self.width,
            x = self.width * 0.03,
            y = self.height * 0.03,
            spacing = 50.0)

    def _render_history(self):
        glColor4f(0.8,0.8,0.8,1)
        for location, frequency in self._locations.iteritems():
            glPointSize(pow(float(frequency) / self._max_frequency, 0.15) * 4 / 1024 * self.width)
            glBegin(GL_POINTS)
            glVertex2f(location.x * self.width, self.height - location.y * self.height)
            glEnd()

    def _render_activity(self):
        glColor4f(1,1,1,1)
        for segment in self.playing_segments.values():
            location = self.peers_by_addr[segment.peer.addr].location
            x, y = location

            n = clamp(int(segment.relative_size() * MARKER_PRECISION), 0, MARKER_PRECISION-1)
            glPushMatrix()
            glTranslatef(x * self.width, self.height - y * self.height, 0)
            glCallList(self._marker_lists[n])
            glPopMatrix()

    def _render_marker_circle(self, n):
        radius = float(n) / MARKER_PRECISION * 10.0/1024 * self.width

        glColor4f(1,1,1,1)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, 0)
        for i in range(20):
            a1 = float(i) / 20 * 2*math.pi
            a2 = float(i+1) / 20 * 2*math.pi
            x1 = radius * math.cos(a1)
            y1 = radius * math.sin(a1)
            x2 = radius * math.cos(a2)
            y2 = radius * math.sin(a2)
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)
        glEnd()

    def _update(self):
        outdated = []
        for segment in self.playing_segments.values():
            if not segment.is_playing():
                outdated.append(segment.id)

        for segment_id in outdated:
            del self.playing_segments[segment_id]

parser = ArgumentParser()
HeatMap.add_parser_arguments(parser)
options = parser.parse_args()
HeatMap(options).run()
