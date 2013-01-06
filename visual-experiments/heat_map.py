#!/usr/bin/python

from argparse import ArgumentParser
import collections
import math

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from vector import Vector2d
from OpenGL.GL import *

sys.path.append("geo")
import locations

MARKER_PRECISION = 20

def clamp(value, min_value, max_value):
    return max(min(max_value, value), min_value)

class Location(Vector2d):
    def __init__(self, x_y_tuple):
        x, y = x_y_tuple
        Vector2d.__init__(self, x, y)

class File(visualizer.File):
    def add_segment(self, segment):
        location = self.visualizer.peers_by_addr[segment.peer.addr].location
        if location:
            self.visualizer.added_segment(segment)

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.arrival_time = self.visualizer.current_time()
        self.visualizer.added_peer(self)

class Segment(visualizer.Segment):
    def relative_size(self):
        return math.sin(self.relative_age() * 2*math.pi)

class HeatMap(visualizer.Visualizer):
    def __init__(self, args):
        self._history_layer = None
        self._load_locations()
        visualizer.Visualizer.__init__(
            self, args, file_class=File, peer_class=Peer, segment_class=Segment)
        self.playing_segments = collections.OrderedDict()

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
        self._history_layer.draw()
        self._render_activity()

    def _render_history(self):
        glColor4f(1,1,1,1)
        for location, frequency in self._locations.iteritems():
            glPointSize(pow(float(frequency) / self._max_frequency, 0.15) * 6 / 640 * self.width)
            glBegin(GL_POINTS)
            glVertex2f(location.x * self.width, location.y * self.height)
            glEnd()

    def _render_activity(self):
        glColor4f(1,1,1,1)
        for segment in self.playing_segments.values():
            location = self.peers_by_addr[segment.peer.addr].location
            x, y = location

            #n = int(MARKER_PRECISION * (((self.now - segment.peer.arrival_time) * 0.8))) % MARKER_PRECISION
            n = clamp(int(segment.relative_size() * MARKER_PRECISION), 0, MARKER_PRECISION-1)
            glPushMatrix()
            glTranslatef(x * self.width, y * self.height, 0)
            glCallList(self._marker_lists[n])
            glPopMatrix()

            # size = (1.0 + 0.3 * math.sin((self.now - segment.peer.arrival_time) * 2.0)) * 8 / 640
            # glPointSize(size * self.width)
            # glBegin(GL_POINTS)
            # glVertex2f(x * self.width, y * self.height)
            # glEnd()

    def _render_marker_circle(self, n):
        glLineWidth(2.0 / 1024 * self.width)
        # t = float(n) / MARKER_PRECISION * 2*math.pi
        # radius = (1.0 + 0.15 * math.sin(t)) * 8 / 640
        radius = float(n) / MARKER_PRECISION * 8 / 640
        glBegin(GL_LINE_LOOP)
        for i in range(20):
            a = float(i) / 20 * 2*math.pi
            cx = radius * math.cos(a) * self.min_dimension
            cy = radius * math.sin(a) * self.min_dimension
            glVertex2f(cx, cy)
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
