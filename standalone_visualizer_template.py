#!/usr/bin/python

from argparse import ArgumentParser

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *

class MyVisualizer(visualizer.Visualizer):
    def render(self):
        pass

parser = ArgumentParser()
MyVisualizer.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True
MyVisualizer(options).run()
