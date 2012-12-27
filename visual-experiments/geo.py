#!/usr/bin/python

import sys
from argparse import ArgumentParser
import numpy
import re
import math
import collections
import cPickle

sys.path.append("geo")
import world
import ip_locator
import random
from gps import GPS
import os

import visualizer
from OpenGL.GL import *
from vector import Vector3d, Vector

LAND_COLOR = (.5, .5, .5)
BARS_TOP = -5
BARS_BOTTOM = 0

CAMERA_POSITION = Vector(3, [-17.237835534835536, -14.099999999999966, -24.48634534467994])
CAMERA_Y_ORIENTATION = -1
CAMERA_X_ORIENTATION = 38

HERE_LATITUDE = 52.500556
HERE_LONGITUDE = 13.398889

WORLD_WIDTH = 30
WORLD_HEIGHT = 20
LOCATION_PRECISION = 200

class File(visualizer.File):
    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.visualizer.added_segment(segment)

class Geography(visualizer.Visualizer):
    def __init__(self, args):
        self._ip_locator = ip_locator.IpLocator()
        self._gps = GPS(WORLD_WIDTH, WORLD_HEIGHT)
        self._here_x = self._gps.x(HERE_LONGITUDE)
        self._here_y = self._gps.y(HERE_LATITUDE)
        self._load_locations()
        visualizer.Visualizer.__init__(self, args, file_class=File)
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self._world = world.World(WORLD_WIDTH, WORLD_HEIGHT)
        self.enable_3d()
        self.playing_segments = collections.OrderedDict()
        self._stable_layer = self.new_layer(self._render_world_and_history)
        #self._load_traces()

    def _load_traces(self):
        #f = open("sessions/120827-084403-TDL4/traces.data", "r")
        f = open("sessions/121104-171222-TDL4-slow/traces.data", "r")
        self._traces = cPickle.load(f)
        f.close()

    def _load_locations(self):
        self._locations = []
        self._grid = numpy.zeros((LOCATION_PRECISION, LOCATION_PRECISION), int)
        self._addrs = set()
        #self._add_random_locations()
        self._add_peers_from_log()

    def _add_peers_from_log(self):
        f = open("%s/../geo/scanner/peers.log" % os.path.dirname(__file__), "r")
        r = re.compile('^peer \[([0-9.]+)\]')
        for line in f:
            m = r.search(line)
            if m:
                addr = m.group(1)
                self._add_ip(addr)
        f.close()

    def _add_random_locations(self):
        n = 0
        while n < 10000:
            addr = ".".join([str(random.randint(0,255)) for i in range(4)])
            if self._add_ip(addr):
                n += 1

    def _add_ip(self, addr):
        if not addr in self._addrs:
            location_info = self._addr_location(addr)
            if location_info:
                x, y, nx, ny = location_info
                self._locations.append((x, y))
                self._grid[ny, nx] += 1
                self._addrs.add(addr)
                return True

    def _addr_location(self, addr):
        location = self._ip_locator.locate(addr)
        if location:
            x, y = location
            nx = int(LOCATION_PRECISION * x)
            ny = int(LOCATION_PRECISION * y)
            return x, y, nx, ny

    def added_segment(self, segment):
        self._add_ip(segment.peer.addr)
        self.playing_segments[segment.id] = segment

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        self.update()
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._stable_layer.draw()
        self._render_grid_activity()
        #self._render_active_traces()

    def _render_world_and_history(self):
        self._location_max_value = numpy.max(self._grid)
        #self._render_world()

        self._render_bar_grid_lines()
        self._render_bar_grid_points()

        #self._render_parabolae()
        #self._render_land_points()

        #self._render_locations()

    def update(self):
        self._grid_activity = numpy.zeros((LOCATION_PRECISION, LOCATION_PRECISION), int)
        outdated = []
        for segment in self.playing_segments.values():
            if segment.is_playing():
                location_info = self._addr_location(segment.peer.addr)
                if location_info:
                    x, y, nx, ny = location_info
                    self._grid_activity[ny, nx] = 1
            else:
                outdated.append(segment.id)

        if len(outdated) > 0:
            for segment_id in outdated:
                del self.playing_segments[segment_id]

    def _render_world(self):
        glColor3f(*LAND_COLOR)

        for path in self._world.paths:
            self._render_land(path)

    def _render_land(self, path):
        glBegin(GL_LINE_STRIP)
        for x, y in path:
            glVertex3f(x, 0, y)
        glEnd()

    def _render_locations(self):
        glColor4f(1, 1, 1, .01)
        glBegin(GL_LINES)
        for lx, ly in self._locations:
            x = lx * WORLD_WIDTH
            y = ly * WORLD_HEIGHT
            glVertex3f(x, BARS_BOTTOM, y)
            glVertex3f(x, BARS_TOP, y)
        glEnd()

    def _render_bar_grid_lines(self):
        glColor4f(1, 1, 1, 0.2)
        glBegin(GL_LINES)
        ny = 0
        for row in self._grid:
            y = (ny+0.5) / LOCATION_PRECISION * WORLD_HEIGHT
            nx = 0
            for value in row:
                if value > 0:
                    strength = pow(float(value) / self._location_max_value, 0.2)
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH

                    # glColor4f(1, 1, 1, 0.5 * strength)
                    # glVertex3f(x, BARS_TOP, y)
                    # glColor4f(1, 1, 1, 0.05)
                    # glVertex3f(x, BARS_BOTTOM, y)

                    glVertex3f(x, BARS_TOP, y)
                    glVertex3f(x, BARS_TOP - strength*BARS_TOP, y)
                nx += 1
            ny += 1
        glEnd()

    def _render_bar_grid_points(self):
        self._render_grid_points(BARS_TOP)

    def _render_grid_points(self, h):
        glEnable(GL_POINT_SMOOTH)
        glPointSize(3.0)
        glBegin(GL_POINTS)
        glColor4f(1, 1, 1, 0.5)
        ny = 0
        for row in self._grid:
            y = (ny+0.5) / LOCATION_PRECISION * WORLD_HEIGHT
            nx = 0
            for value in row:
                if value > 0:
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH
                    glVertex3f(x, h, y)
                nx += 1
            ny += 1
        glEnd()

    def _render_parabolae(self):
        ny = 0
        for row in self._grid:
            y = (ny+0.5) / LOCATION_PRECISION * WORLD_HEIGHT
            nx = 0
            for value in row:
                if value > 0:
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH
                    strength = pow(float(value) / self._location_max_value, 0.4) * 0.5
                    glColor4f(1, 1, 1, strength)
                    self._render_parabola(x, y, self._here_x, self._here_y)
                nx += 1
            ny += 1

    def _render_grid_activity(self):
        glBegin(GL_LINES)
        ny = 0
        for row in self._grid_activity:
            y = (ny+0.5) / LOCATION_PRECISION * WORLD_HEIGHT
            nx = 0
            for value in row:
                if value > 0:
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH
                    glColor4f(1, 1, 1, 1)
                    #self._render_parabola(x, y, self._here_x, self._here_y)
                    glVertex3f(x, BARS_TOP, y)
                    glColor4f(1, 1, 1, 0.25)
                    glVertex3f(x, BARS_BOTTOM, y)
                nx += 1
            ny += 1
        glEnd()

    def _render_parabola(self, x1, y1, x2, y2):
        h1 = 0
        h2 = 2
        glBegin(GL_LINE_STRIP)
        precision = 100
        for n in range(precision):
            r = float(n) / (precision - 1)
            x = x1 + (x2 - x1) * r
            y = y1 + (y2 - y1) * r
            h = h1 + (h2 - h1) * (math.cos((r - 0.5) / 5) - 0.995) / 0.005
            glVertex3f(x, h, y)
        glEnd()

    def _render_land_points(self):
        self._render_grid_points(0)

    def _render_active_traces(self):
        for segment in self.playing_segments.values():
            trace = self._traces[segment.peer.addr]
            self._render_trace(trace)

    def _render_trace(self, trace):
        glColor4f(1,1,1,1)
        glBegin(GL_LINE_STRIP)
        n = 1
        for lx, ly in trace:
            #opacity = float(n) / (len(trace)-1)
            #glColor4f(1,1,1, opacity)
            x = lx * WORLD_WIDTH
            y = ly * WORLD_HEIGHT
            glVertex3f(x, 0, y)
            n += 1
        glEnd()

visualizer.run(Geography)
