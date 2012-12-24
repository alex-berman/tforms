#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
from session import Session
from interpret import Interpreter
from ancestry_tracker import AncestryTracker, Piece
from vector import Vector2d
import random

import sys
sys.path.append("visual-experiments")
import rectangular_visualizer as visualizer
from OpenGL.GL import *

class Node:
    def __init__(self, id):
        self.id = id
        self.velocity = Vector2d(0, 0)
        self.position = Vector2d(random.uniform(0,1),
                                 random.uniform(0,1))
        self.edges = []

    def add_edge(self, edge):
        self.edges.append(edge)

class Ancestry(visualizer.Visualizer):
    def __init__(self, pieces, args):
        visualizer.Visualizer.__init__(self, args)
        self._tracker = AncestryTracker()
        for chunk in pieces:
            self._tracker.add(Piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"]))
        self._nodes = {}
        self._override_recursion_limit()
        for piece in self._tracker.last_pieces():
            self._follow_piece(piece)

    def _follow_piece(self, piece):
        node = Node(piece.id)
        for parent in piece.parents.values():
            node.add_edge(parent.id)
            self._follow_piece(parent)
        self._nodes[piece.id] = node
        
    def _override_recursion_limit(self):
        sys.setrecursionlimit(max(len(self._tracker.pieces()), sys.getrecursionlimit()))

    def render(self):
        self._update()

        glColor3f(0,0,0)
        self._min_x = min([node.position.x for node in self._nodes.values()])
        self._max_x = max([node.position.x for node in self._nodes.values()])
        self._min_y = min([node.position.y for node in self._nodes.values()])
        self._max_y = max([node.position.y for node in self._nodes.values()])

        for node in self._nodes.values():
            self._render_node(node)

    def _render_node(self, node):
        glPointSize(3.0)
        glBegin(GL_POINTS)
        px = self._px(node.position.x)
        py = self._py(node.position.y)
        glVertex2f(px, py)
        glEnd()

        glBegin(GL_LINES)
        for other_node_id in node.edges:
            other_node = self._nodes[other_node_id]
            glVertex2f(px, py)
            glVertex2f(self._px(other_node.position.x),
                       self._py(other_node.position.y))
        glEnd()

    def _px(self, x):
        return (x - self._min_x) / (self._max_x - self._min_x) * self.width

    def _py(self, y):
        return (y - self._min_y) / (self._max_y - self._min_y) * self.height

    def _update(self):
        for node in self._nodes.values():
            node.force = Vector2d(0,0)
        for node in self._nodes.values():
            self._get_node_force(node)
        for node in self._nodes.values():
            self._apply_node_force(node)

    def _get_node_force(self, node):
        for other_node_id in node.edges:
            other_node = self._nodes[other_node_id]
            self.apply_hooke_attraction(node, other_node)
            self.apply_hooke_attraction(other_node, node)

        for other_node in self._nodes.values():
            if other_node != node:
                self.apply_coulomb_repulsion(node, other_node)

    def _apply_node_force(self, node):
        node.velocity += node.force * 0.01
        node.position += node.velocity

    def apply_coulomb_repulsion(self, f, other):
        d = f.position - other.position
        distance = d.mag()
        if distance == 0:
            f.force += Vector2d(random.uniform(0.0, 0.0001),
                                random.uniform(0.0, 0.0001))
        else:
            d.normalize()
            f.force += d / pow(distance, 2)

    def apply_hooke_attraction(self, f, other):
        d = other.position - f.position
        f.force += d

parser = ArgumentParser()
parser.add_argument("sessiondir")
Ancestry.add_parser_arguments(parser)
options = parser.parse_args()
options.standalone = True

sessiondir = options.sessiondir
logfilename = "%s/session.log" % sessiondir

print "session: %s" % sessiondir

tr_log = TrLogReader(logfilename).get_log()
print >> sys.stderr, "found %d chunks" % len(tr_log.chunks)
tr_log.ignore_non_downloaded_files()

pieces = Interpreter().interpret(tr_log.chunks)
Ancestry(pieces, options).run()
