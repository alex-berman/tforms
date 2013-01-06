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

class Location(Vector2d):
    def __init__(self, x_y_tuple):
        x, y = x_y_tuple
        Vector2d.__init__(self, x, y)

class File(visualizer.File):
    def add_segment(self, segment):
        location = self.visualizer.peers_by_addr[segment.peer.addr].location
        if location:
            self.visualizer.playing_segment(segment)
            self.visualizer.added_segment(segment)

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.arrival_time = self.visualizer.current_time()

class HeatMap(visualizer.Visualizer):
    def __init__(self, args):
        self._load_locations()
        visualizer.Visualizer.__init__(self, args, file_class=File, peer_class=Peer)
        self.playing_segments = collections.OrderedDict()

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def _load_locations(self):
        self._locations = collections.defaultdict(int)
        for location in locations.get_locations():
            self._add_location(location)
        self._max_frequency = max(self._locations.values())

    def _add_location(self, location):
        if not location:
            return
        self._locations[Location(location)] += 1

    def added_segment(self, segment):
        self._add_location(self.peers_by_addr[segment.peer.addr].location)
        self.playing_segments[segment.id] = segment

    def render(self):
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._render_history()
        self._render_activity()

    def _render_history(self):
        glColor4f(1,1,1,1)
        for location, frequency in self._locations.iteritems():
            glPointSize(pow(float(frequency) / self._max_frequency, 0.3) * 8 / 640 * self.width)
            glBegin(GL_POINTS)
            glVertex2f(location.x * self.width, location.y * self.height)
            glEnd()

    def _render_activity(self):
        glColor4f(1,1,1,1)
        for segment in self.playing_segments.values():
            location = self.peers_by_addr[segment.peer.addr].location
            x, y = location
            # frequency = self._locations[Location(location)]
            # amplitude = pow(float(frequency) / self._max_frequency, 0.3)
            # amplitude *= (1.0 + 0.3 * math.sin((self.now - segment.peer.arrival_time) * 2.0))
            # size = amplitude * 8 / 640
            size = (1.0 + 0.3 * math.sin((self.now - segment.peer.arrival_time) * 2.0)) * 8 / 640
            glPointSize(size * self.width)
            glBegin(GL_POINTS)
            glVertex2f(x * self.width, y * self.height)
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
