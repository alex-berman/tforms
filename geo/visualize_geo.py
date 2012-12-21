#!/usr/bin/python

import world
import sys
from argparse import ArgumentParser

import GeoIP
import random
from gps import GPS
import os

sys.path.append("visual-experiments")
import visualizer
from OpenGL.GL import *
from vector import Vector3d, Vector

LAND_COLOR = (1,1,1)
BAR_COLOR = (1,1,1,.01)
BARS_TOP = 6
BARS_BOTTOM = 0

CAMERA_POSITION = Vector(3, [-11.410326069762691, -7.499999999999989, -33.71008311478789])
CAMERA_Y_ORIENTATION = 0
CAMERA_X_ORIENTATION = 1

WORLD_WIDTH = 20
WORLD_HEIGHT = 20

gi = GeoIP.open("%s/GeoLiteCity.dat" % os.path.dirname(__file__), GeoIP.GEOIP_STANDARD)
gps = GPS(WORLD_WIDTH, WORLD_HEIGHT)
locations = []

n = 0
while n < 10000:
    addr = ".".join([str(random.randint(0,255)) for i in range(4)])
    gir = gi.record_by_addr(addr)
    if gir:
        x = gps.x(gir['longitude'])
        y = gps.y(gir['latitude'])
        locations.append((x,y))
        n += 1

class Geography(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args)
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self._world = world.World(WORLD_WIDTH, WORLD_HEIGHT)
        self.enable_3d()

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        self._render_world()
        self._render_bars()

    def _render_world(self):
        glColor3f(*LAND_COLOR)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for path in self._world.paths:
            self._render_land(path)

    def _render_land(self, path):
        glBegin(GL_LINE_STRIP)
        for x, y in path:
            glVertex3f(x, 0, y)
        glEnd()

    def _render_bars(self):
        glColor4f(*BAR_COLOR)
        glBegin(GL_LINES)
        for x,y in locations:
            glVertex3f(x, BARS_BOTTOM, y)
            glVertex3f(x, BARS_TOP, y)
        glEnd()

parser = ArgumentParser()
Geography.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

Geography(options).run()
