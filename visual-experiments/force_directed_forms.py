import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from boid import Boid
from vector import Vector
import copy
import math
import random
from springs import spring_force

CHUNK_SIZE_FACTOR = 0.000001
SOUNDING_CHUNK_SIZE_FACTOR = CHUNK_SIZE_FACTOR * 1.5
MAX_CHUNK_SIZE = 5.0 / 640
INNER_MARGIN = 20.0 / 640

class TargetType:
    (PIECE, CHUNK, NEW_PIECE) = range(3)

class Chunk(visualizer.Chunk):
    def append(self, other):
        visualizer.Chunk.append(self, other)
        self.move_randomly(self.end_position)

    def prepend(self, other):
        visualizer.Chunk.prepend(self, other)
        self.move_randomly(self.begin_position)

    def move_randomly(self, position):
        angle = random.uniform(0, 2 * math.pi)
        distance = 1.0
        movement = Vector(distance * math.cos(angle),
                          distance * math.sin(angle))
        self.end_position += movement

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        
    def add_chunk(self, chunk):
        chunk.boid = Boid(self.get_departure_position(chunk), 10.0, 3.0)
        chunk.target = None
        chunk.target_type = None
        chunk.target_position = None
        chunk.target_position = self.get_target_position(chunk)
        chunk.boid.arrive(chunk.target_position)
        chunk.arrived = False
        self.arriving_chunks[chunk.id] = chunk

    def stopped_playing(self, chunk_id):
        chunk = self.arriving_chunks[chunk_id]
        del self.arriving_chunks[chunk_id]
        # TODO: verify that these positions are really OK
        chunk.begin_position = Vector(chunk.boid.loc.x, chunk.boid.loc.y)
        chunk.end_position = Vector(chunk.boid.loc.x, chunk.boid.loc.y)
        self.gatherer.add(chunk)
        self.reorient_chunks_following(chunk)

    def get_departure_position(self, chunk):
        if chunk.pan < 0.5:
            x = 0
        else:
            x = self.visualizer.width
        y = chunk.height * self.visualizer.height
        return Vector(x, y)

    def get_target_position(self, chunk):
        if not chunk.target_position:
            self.find_target(chunk)
        return chunk.target_position

    def find_target(self, chunk):
        position = self.find_joinable_piece(chunk)
        if position:
            chunk.target_type = TargetType.PIECE
            chunk.target_position = position
            return

        other_chunk = self.find_other_huntable_chunk(chunk)
        if other_chunk:
            chunk.target_type = TargetType.CHUNK
            chunk.target = other_chunk
            chunk.target_position = other_chunk.boid.loc
            return

        if len(self.gatherer.pieces()) > 0:
            chunk.target_position = self.close_to_existing_piece()
            return

        chunk.target_type = TargetType.NEW_PIECE
        chunk.target_position = self.anywhere()

    def anywhere(self):
        return Vector(random.uniform(self.visualizer.width * INNER_MARGIN,
                                     self.visualizer.width * (1 - INNER_MARGIN*2)),
                      random.uniform(self.visualizer.height * INNER_MARGIN,
                                     self.visualizer.height * (1 - INNER_MARGIN*2)))

    def close_to_existing_piece(self):
        piece = random.choice(self.gatherer.pieces())
        position = random.choice([piece.begin_position,
                                  piece.end_position])
        angle = random.uniform(0, 2 * math.pi)
        distance = 1.0
        movement = Vector(distance * math.cos(angle),
                          distance * math.sin(angle))
        return position + movement

    def find_joinable_piece(self, chunk):
        appendable_piece_key = self.gatherer.find_appendable_piece(chunk)
        prependable_piece_key = self.gatherer.find_prependable_piece(chunk)
        if appendable_piece_key and prependable_piece_key:
            appendable_position = self.gatherer.piece(appendable_piece_key).begin_position
            prepandable_position = self.gatherer.piece(prependable_piece_key).end_position
            chunk.target_position = (appendable_position + prepandable_position) / 2
        elif appendable_piece_key:
            return self.gatherer.piece(appendable_piece_key).begin_position
        elif prependable_piece_key:
            return self.gatherer.piece(prependable_piece_key).end_position
    
    def find_other_huntable_chunk(self, chunk):
        # optimization: iterate appendables in reverse order, or use some kind of cache
        for other in self.arriving_chunks.values():
            if other.end == chunk.begin:
                return other
            if other.begin == chunk.end:
                return other

    def reorient_chunks_following(self, targeted_chunk):
        for chunk in self.arriving_chunks.values():
            if chunk.target_type == TargetType.CHUNK and \
                    chunk.target == targeted_chunk:
                self.find_target(chunk)

    def update(self):
        self.update_pieces()
        self.update_arriving_chunks()

    def update_pieces(self):
        for piece in self.gatherer.pieces():
            self.get_piece_force(piece)
        for piece in self.gatherer.pieces():
            self.apply_piece_force(piece)

    def get_piece_force(self, piece):
        piece.desired_length = self.desired_piece_length(piece)
        piece.begin_force = Vector(0,0)
        piece.end_force = Vector(0,0)
        self.consider_desired_length(piece, piece.begin_force, piece.begin_position, piece.end_position)
        self.consider_desired_length(piece, piece.end_force, piece.end_position, piece.begin_position)
        piece.begin_force.limit(3.0)
        piece.end_force.limit(3.0)

    def desired_piece_length(self, piece):
        return 100.0

    def consider_desired_length(self, piece, force, position, opposite_position):
        force += spring_force(position, opposite_position, piece.desired_length)

    def apply_piece_force(self, piece):
        piece.begin_position += piece.begin_force
        piece.end_position += piece.end_force

    def update_arriving_chunks(self):
        for chunk in self.arriving_chunks.values():
            if not chunk.arrived:
                chunk.boid.update()
                if self.arrived(chunk):
                    self.visualizer.play_chunk(chunk)
                    chunk.arrived = True

    def arrived(self, chunk):
        if chunk.target_type in [TargetType.PIECE,
                                 TargetType.NEW_PIECE]:
            distance = (chunk.target_position - chunk.boid.loc).mag()
            return distance < 1.0
        else:
            return False

class ForcedDirectedForms(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, Chunk)
        self.files = {}

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        if not chunk.filenum in self.files:
            self.files[chunk.filenum] = File(chunk.file_length, self)
        self.files[chunk.filenum].add_chunk(chunk)

    def stopped_playing(self, chunk_id, filenum):
        self.files[filenum].stopped_playing(chunk_id)

    def render(self):
        for f in self.files.values():
            f.update()
        self.draw_gathered_chunks()
        self.draw_arriving_chunks()
        self.draw_sounding_chunks()
        
    def draw_gathered_chunks(self):
        for f in self.files.values():
            for chunk in f.gatherer.pieces():
                self.draw_completed_piece(chunk, f)

    def draw_arriving_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                if not chunk.playing:
                    self.draw_travelling_chunk(chunk, f)

    def draw_sounding_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                if chunk.playing:
                    self.draw_sounding_chunk(chunk, f)

    def draw_travelling_chunk(self, chunk, f):
        opacity = 0.3
        size = chunk.byte_size * CHUNK_SIZE_FACTOR * self.width
        self.draw_point(chunk.boid.loc.x,
                        chunk.boid.loc.y,
                        size, opacity)

    def draw_point(self, x, y, size, opacity):
        size = min(size, MAX_CHUNK_SIZE * self.width)
        size = max(size, 1.0)
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    def draw_completed_piece(self, piece, f):
        size = 3
        opacity = 0.5
        self.draw_point(piece.begin_position.x,
                        piece.begin_position.y,
                        size, opacity)
        self.draw_point(piece.end_position.x,
                        piece.end_position.y,
                        size, opacity)

    def draw_sounding_chunk(self, chunk, f):
        opacity = 1
        size = chunk.byte_size * SOUNDING_CHUNK_SIZE_FACTOR * self.width
        self.draw_point(chunk.target_position.x,
                        chunk.target_position.y,
                        size, opacity)

visualizer.run(ForcedDirectedForms)
