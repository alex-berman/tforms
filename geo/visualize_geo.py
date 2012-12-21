#!/usr/bin/python

import world
import sys
from argparse import ArgumentParser
import numpy

import GeoIP
import random
from gps import GPS
import os

sys.path.append("visual-experiments")
import visualizer
from OpenGL.GL import *
from vector import Vector3d, Vector

LAND_COLOR = (1,1,1)
BARS_TOP = 10
BARS_BOTTOM = 0

CAMERA_POSITION = Vector(3, [-11.410326069762691, -14.999999999999963, -33.71008311478789])
CAMERA_Y_ORIENTATION = 2
CAMERA_X_ORIENTATION = 19

WORLD_WIDTH = 20
WORLD_HEIGHT = 20
LOCATION_PRECISION = 200

class Geography(visualizer.Visualizer):
    def __init__(self, args):
        self._geo_ip = GeoIP.open("%s/GeoLiteCity.dat" % os.path.dirname(__file__), GeoIP.GEOIP_STANDARD)
        self._gps = GPS(WORLD_WIDTH, WORLD_HEIGHT)
        self._load_locations()
        visualizer.Visualizer.__init__(self, args)
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self._world = world.World(WORLD_WIDTH, WORLD_HEIGHT)
        self.enable_3d()

    def _load_locations(self):
        self._locations = []
        self._grid = numpy.zeros((LOCATION_PRECISION, LOCATION_PRECISION), int)
        n = 0
        while n < 10000:
            addr = ".".join([str(random.randint(0,255)) for i in range(4)])
            if self._add_ip(addr):
                n += 1
        self._location_max_value = numpy.max(self._grid)

    def _add_ip(self, addr):
        gir = self._geo_ip.record_by_addr(addr)
        if gir:
            x = self._gps.x(gir['longitude'])
            y = self._gps.y(gir['latitude'])
            nx = int(LOCATION_PRECISION * x/WORLD_WIDTH)
            ny = int(LOCATION_PRECISION * y/WORLD_HEIGHT)
            self._locations.append((x, y))
            self._grid[ny, nx] += 1
            return True

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self._render_world()
        self._render_bar_grid()
        self._render_surface_points()
        #self._render_locations()

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
        for x,y in self._locations:
            glVertex3f(x, BARS_BOTTOM, y)
            glVertex3f(x, BARS_TOP, y)
        glEnd()

    def _render_bar_grid(self):
        glBegin(GL_LINES)
        glColor4f(1, 1, 1, 0.2)
        ny = 0
        for row in self._grid:
            y = (ny+0.5) / LOCATION_PRECISION * WORLD_HEIGHT
            nx = 0
            for value in row:
                if value > 0:
                    h = pow(float(value) / self._location_max_value, 0.2)
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH
                    glVertex3f(x, BARS_TOP - h*BARS_TOP, y)
                    glVertex3f(x, BARS_TOP, y)
                nx += 1
            ny += 1
        glEnd()

    def _render_surface_points(self):
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
                    h = pow(float(value) / self._location_max_value, 0.2)
                    x = (nx+0.5) / LOCATION_PRECISION * WORLD_WIDTH
                    glVertex3f(x, BARS_TOP, y)
                nx += 1
            ny += 1
        glEnd()

parser = ArgumentParser()
Geography.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

Geography(options).run()
