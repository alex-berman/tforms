#!/usr/bin/python

import world
import sys
sys.path.append("visual-experiments")
import visualizer
from OpenGL.GL import *

CAMERA_POSITION = Vector3d(-4.6, -0.6, -8.6)
CAMERA_Y_ORIENTATION = -37
CAMERA_X_ORIENTATION = 0

class Geography(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args)
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self._world = world.World(1.0, 1.0)

    def render(self):
        self._render_world()

    def _render_world(self):


parser = ArgumentParser()
Geography.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

Ancestry(options).run()
