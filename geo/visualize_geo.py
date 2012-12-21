#!/usr/bin/python

import world
import sys
from argparse import ArgumentParser

sys.path.append("visual-experiments")
import visualizer
from OpenGL.GL import *
from vector import Vector3d, Vector

LAND_COLOR = (1,1,1)

CAMERA_POSITION = Vector(3, [-11.410326069762691, -7.499999999999989, -33.71008311478789])
CAMERA_Y_ORIENTATION = 0
CAMERA_X_ORIENTATION = 1

class Geography(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args)
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self._world = world.World(20.0, 20.0)
        self.enable_3d()

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        self._render_world()

    def _render_world(self):
        glColor3f(*LAND_COLOR)
        for path in self._world.paths:
            self._render_land(path)

    def _render_land(self, path):
        glBegin(GL_LINE_STRIP)
        for x, y in path:
            glVertex3f(x, 0, y)
        glEnd()


parser = ArgumentParser()
Geography.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

Geography(options).run()
