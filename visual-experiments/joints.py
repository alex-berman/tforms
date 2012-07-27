import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from vector import Vector, DirectionalVector
import copy
import math
import random
from springs import spring_force

JOINT_SIZE = 3.0 / 640
INNER_MARGIN = 20.0 / 640
OUTER_MARGIN = 40

class JointPosition(Vector):
    def __init__(self, joint):
        self.joint = joint
        Vector.__init__(self, 0,0)

    def __repr__(self):
        return 'JointPosition(%s, %s, %s)' % (self.joint, self.x, self.y)

class Joint:
    def __init__(self, chunk, byte_position, neighbour_type, direction):
        self.chunk = chunk
        self.byte_position = byte_position
        self.neighbour_type = neighbour_type
        self.direction = direction
        self.target_position = self.find_target_position()
        self.position = JointPosition(self)
        self.reposition()

    def find_target_position(self):
        joint = self.find_neighbour_joint_among_chunks(
            self.chunk.file.arriving_chunks.values())
        if joint:
            return joint.position

        joint = self.find_neighbour_joint_among_chunks(
            self.chunk.file.gatherer.pieces())
        if joint:
            return joint.position

    def find_neighbour_joint_among_chunks(self, chunks):
        for chunk in chunks:
            if chunk != self.chunk:
                joint = chunk.joints[self.neighbour_type]
                if joint.byte_position == self.byte_position:
                    return joint

    def reposition(self):
        self.position.set(self.chunk.position +
                          DirectionalVector(self.chunk.angle,
                                            self.chunk.length/2) * self.direction)

    def arrived(self):
        if self.target_position:
            if not (isinstance(self.target_position, JointPosition) \
                        and not self.target_position.joint.chunk.has_arrived):
                distance = (self.target_position - self.position).mag()
                return distance < 2.0

class Chunk(visualizer.Chunk):
    def setup(self):
        self.length = 15.0 # TEMP
        self.angle = random.uniform(0, 2*math.pi)
        self.position = self.get_departure_position()
        self.joints = {"begin": Joint(self, self.begin, "end", -1),
                       "end":   Joint(self, self.end, "begin", 1)}
        self.begin_position = self.joints["begin"].position
        self.end_position = self.joints["end"].position
        self.has_arrived = False
        if not self.has_target():
            self.pick_random_target()

    def has_target(self):
        for joint in self.joints.values():
            if joint.target_position:
                return True

    def pick_random_target(self):
        self.joints["begin"].target_position = Vector(
            random.uniform(self.visualizer.width * INNER_MARGIN,
                           self.visualizer.width * (1 - INNER_MARGIN*2)),
            random.uniform(self.visualizer.height * INNER_MARGIN,
                           self.visualizer.height * (1 - INNER_MARGIN*2)))

    def get_departure_position(self):
        if self.pan < 0.5:
            x = -OUTER_MARGIN
        else:
            x = self.visualizer.width + OUTER_MARGIN
        y = self.height * self.visualizer.height
        return Vector(x, y)

    def update(self):
        self.force = Vector(0,0)
        self.attract_to_neighbours()
        self.force.limit(6.0)
        self.position += self.force
        for joint in self.joints.values():
            joint.reposition()
        self.angle = self.move_angle_towards(self.angle, self.force.angle(), 0.2)

    def move_angle_towards(self, angle, target, amount):
        return self.clamp_angle(angle + self.subtract_angle(target, angle) * amount)

    def subtract_angle(self, x, y):
        if abs(x - y) < math.pi:
            return x - y
        elif x > y:
            return -2*math.pi - x + y
        else:
            return 2*math.pi + x - y

    def clamp_angle(self, x):
        while x < 0:
            x += 2*math.pi
        while x > 2*math.pi:
            x -= 2*math.pi
        return x
        
    def attract_to_neighbours(self):
        for joint in self.joints.values():
            if joint.target_position:
                self.force += spring_force(joint.position,
                                           joint.target_position,
                                           1.0) * 0.3

    def arrived(self):
        for joint in self.joints.values():
            if joint.arrived():
                return True

    def append(self, other):
        visualizer.Chunk.append(self, other)
        self.joints["end"].position.set(other.joints["end"].position)

    def prepend(self, other):
        visualizer.Chunk.append(self, other)
        self.joints["begin"].position.set(other.joints["begin"].position)

    def draw(self):
        self.draw_joints()
        self.draw_line()

    def draw_joints(self):
        opacity = 1.0
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        self.draw_joint(self.begin_position)
        self.draw_joint(self.end_position)

    def draw_joint(self, position):
        size = JOINT_SIZE * self.visualizer.width
        self.draw_point(position.x,
                        position.y,
                        size)

    def draw_point(self, x, y, size):
        glPointSize(size)
        glBegin(GL_POINTS)
        glVertex2f(x, y)
        glEnd()

    def draw_line(self):
        opacity = 0.5
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex2f(self.begin_position.x, self.begin_position.y)
        glVertex2f(self.end_position.x, self.end_position.y)
        glEnd()

class File:
    def __init__(self, length, visualizer):
        self.visualizer = visualizer
        self.arriving_chunks = OrderedDict()
        self.gatherer = Gatherer()
        
    def add_chunk(self, chunk):
        self.arriving_chunks[chunk.id] = chunk
        chunk.setup()

    def update(self):
        self.update_arriving_chunks()

    def update_arriving_chunks(self):
        for chunk in self.arriving_chunks.values():
            chunk.update()
            if chunk.arrived():
                self.gather_chunk(chunk)

    def gather_chunk(self, chunk):
        del self.arriving_chunks[chunk.id]
        chunk.has_arrived = True
        self.gatherer.add(chunk)


class Joints(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args, Chunk)
        self.inner_margin = self.width * INNER_MARGIN
        self.files = {}

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glDisable(GL_BLEND)

    def add_chunk(self, chunk):
        try:
            f = self.files[chunk.filenum]
        except KeyError:
            f = File(chunk.file_length, self)
            self.files[chunk.filenum] = f
        chunk.file = f
        self.files[chunk.filenum].add_chunk(chunk)

    def stopped_playing(self, chunk_id, filenum):
        self.files[filenum].stopped_playing(chunk_id)

    def render(self):
        for f in self.files.values():
            f.update()
        self.draw_gathered_chunks()
        self.draw_arriving_chunks()

    def draw_gathered_chunks(self):
        for f in self.files.values():
            for chunk in f.gatherer.pieces():
                chunk.draw()

    def draw_arriving_chunks(self):
        for f in self.files.values():
            for chunk in f.arriving_chunks.values():
                chunk.draw()

if __name__ == '__main__':
    visualizer.run(Joints)
