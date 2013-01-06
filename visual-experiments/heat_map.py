#!/usr/bin/python

from argparse import ArgumentParser

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *

sys.path.append("geo")
import locations

class HeatMap(visualizer.Visualizer):
    def __init__(self, args):
        self._load_locations()
        visualizer.Visualizer.__init__(self, args)

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def _load_locations(self):
        self._locations = {}
        for location in locations.get_locations():
            self._add_location(location)
        self._max_frequency = max(self._locations.values())

    def _add_location(self, location):
        if not location:
            return
        if location in self._locations:
            self._locations[location] += 1
        else:
            self._locations[location] = 1

    def render(self):
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor3f(1,1,1)
        for location, frequency in self._locations.iteritems():
            x, y = location
            glPointSize(pow(float(frequency) / self._max_frequency, 0.3) * 8 / 640 * self.width)
            glBegin(GL_POINTS)
            glVertex2f(x * self.width, y * self.height)
            glEnd()

parser = ArgumentParser()
HeatMap.add_parser_arguments(parser)
options = parser.parse_args()
HeatMap(options).run()
