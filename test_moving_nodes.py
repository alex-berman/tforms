#!/usr/bin/python

from argparse import ArgumentParser
from vector import Vector2d
import random
import copy

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *

class Node:
    def __init__(self, attractor):
        self.attractor = attractor
        self.position = copy.deepcopy(attractor)
        self.sway_force = Vector2d(0, 0)
        self.attraction_force = Vector2d(0, 0)

    def update(self, time_increment):
        delta = min(time_increment, 1)
        self.sway_force += self.random_vector() * 0.001 * delta
        self.sway_force.limit(0.001)
        self.attraction_force += (self.attractor - self.position) * delta * 0.05
        self.position += self.sway_force
        self.position += self.attraction_force

    def random_vector(self):
        return Vector2d(random.uniform(-0.5, 0.5),
                        random.uniform(-0.5, 0.5))

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
        glVertex2f(node.position.x * self.width,
                   node.position.y * self.height)
        glEnd()

        glBegin(GL_LINES)
        glVertex2f(node.attractor.x * self.width,
                   node.attractor.y * self.height)
        glVertex2f(node.position.x * self.width,
                   node.position.y * self.height)
        glEnd()

parser = ArgumentParser()
MovingNodes.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True
MovingNodes(options).run()
