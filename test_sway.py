#!/usr/bin/python

from argparse import ArgumentParser
from sway import Sway
from vector import Vector2d
import random
import copy

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *

class Node:
    def __init__(self, position):
        self.position = position
        self._sway = Sway()
    
    def update(self, time_increment):
        self._sway.update(time_increment)

    def sway(self):
        return self._sway.sway

class MovingNodes(visualizer.Visualizer):
    def __init__(self, *args):
        visualizer.Visualizer.__init__(self, *args)
        self.nodes = [Node(self.random_position()) for n in range(10)]

    def random_position(self):
        return Vector2d(random.uniform(0,1),
                        random.uniform(0,1))

    def render(self):
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPointSize(10)
        glColor3f(0,0,0)
        for node in self.nodes:
            node.update(self.time_increment)
            self.draw_node(node)

    def draw_node(self, node):
        glBegin(GL_POINTS)
        glVertex2f((node.position.x + node.sway().x) * self.width,
                   (node.position.y + node.sway().y) * self.height)
        glEnd()

        glBegin(GL_LINES)
        glVertex2f((node.position.x + node.sway().x) * self.width,
                   (node.position.y + node.sway().y) * self.height)
        glVertex2f(node.position.x * self.width,
                   node.position.y * self.height)
        glEnd()

parser = ArgumentParser()
MovingNodes.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True
MovingNodes(options).run()
