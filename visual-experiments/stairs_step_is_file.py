import visualizer
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from gatherer import Gatherer
import random
from vector import Vector2d, Vector3d, Vector
from bezier import make_bezier
import colorsys
from smoother import Smoother

NUM_STEPS = 12
STAIRS_WIDTH = 1.5
STEP_HEIGHT = 0.15
STEP_DEPTH = 0.3
WALL_X = -0.5
WALL_TOP = 2
WALL_WIDTH = 0.15

CONTROL_POINTS_BEFORE_BRANCH = 15
CURVE_PRECISION_ON_WALL = 50
CURVE_PRECISION_ON_STEPS = 10
CURVE_OPACITY = 0.8
SEGMENT_DECAY_TIME = 1.0
GATHERED_COLOR_V = (.62, .17, .20)
GATHERED_COLOR_H = (.9, .3, .35)
CURSOR_COLOR_V = (.9, 0, 0)
CURSOR_COLOR_H = (1, 0, 0)
STEPS_COLOR_V = WALL_COLOR_V = (.58, .58, .58)
STEPS_COLOR_H = WALL_COLOR_H = (.9, .9, .9)
CURSOR_THICKNESS = 2.0

# CAMERA_POSITION = Vector3d(-4.6, -0.6, -8.6)
# CAMERA_Y_ORIENTATION = -37
# CAMERA_X_ORIENTATION = 0

CAMERA_POSITION = Vector(3, [-5.093144825477394, -3.8999999999999995, -7.497856691748922])
CAMERA_Y_ORIENTATION = -42
CAMERA_X_ORIENTATION = 25

MIN_GATHERED_SIZE = 0

class Segment(visualizer.Segment):
    def target_position(self):
        return self.wall_step_crossing()

    def wall_step_crossing(self):
        return Vector2d(self.f.z2, self.f.y)

    def decay_time(self):
        return self.age() - self.duration

    def outdated(self):
        return (self.age() - self.duration) > SEGMENT_DECAY_TIME

    def draw_curve(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for z,y in self.curve_on_wall():
            glVertex3f(WALL_X, y, z)
        # if self.is_playing():
        #     for x,z in self.curve_on_step():
        #         glVertex3f(x, self.f.y, z)
        glEnd()

    def curve_on_wall(self):
        control_points = []
        branching_position = self.peer.smoothed_branching_position.value()
        for i in range(CONTROL_POINTS_BEFORE_BRANCH):
            r = float(i) / (CONTROL_POINTS_BEFORE_BRANCH-1)
            control_points.append(self.peer.departure_position * (1-r) +
                                 branching_position * r)
        if self.is_playing():
            target = self.wall_step_crossing()
        else:
            target = branching_position + (self.wall_step_crossing() - branching_position) * \
                (1 - pow(self.decay_time(), 0.3))
        control_points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        return bezier(CURVE_PRECISION_ON_WALL)

    # def curve_on_step(self):
    #     wall_step_crossing_zy = self.wall_step_crossing()
    #     wall_step_crossing = Vector2d(WALL_X, wall_step_crossing_zy[0])
    #     control_points = []
    #     control_points.append(wall_step_crossing)
    #     x = self.f.byte_to_x(self.playback_byte_cursor())
    #     if self.peer.departure_position[0] > self.f.z1:
    #         z = self.f.z1
    #     else:
    #         z = self.f.z2
    #     control_points.append(Vector2d((WALL_X + x) / 2, z))
    #     control_points.append(Vector2d(x, z))
    #     bezier = make_bezier([(p.x, p.y) for p in control_points])
    #     return bezier(CURVE_PRECISION_ON_STEPS)

    def draw_gathered(self):
        self.draw_as_gathered(self.begin, self.end)

    def draw_as_gathered(self, begin, end):
        x1 = self.f.byte_to_x(begin)
        x2 = self.f.byte_to_x(end)
        self.visualizer.set_color(GATHERED_COLOR_H)
        self.draw_xz_polygon(self.f.y,
                             x1, self.f.z1,
                             x2, self.f.z2)

        self.visualizer.set_color(GATHERED_COLOR_V)
        self.draw_xy_polygon(self.f.z2,
                             x1, self.f.y,
                             x2, self.f.neighbour_y)

    def draw_playing(self):
        if self.is_playing():
            self.draw_as_gathered(self.begin, self.playback_byte_cursor())
            self.draw_cursor()

    def draw_cursor(self):
        x = self.f.byte_to_x(self.playback_byte_cursor())
        glLineWidth(CURSOR_THICKNESS)
        self.visualizer.set_color(CURSOR_COLOR_H)
        glBegin(GL_LINES)
        glVertex3f(x, self.f.y, self.f.z1)
        glVertex3f(x, self.f.y, self.f.z2)
        glEnd()

        glBegin(GL_LINES)
        self.visualizer.set_color(CURSOR_COLOR_V)
        glVertex3f(x, self.f.y, self.f.z2)
        glVertex3f(x, self.f.neighbour_y, self.f.neighbour_z1)
        glEnd()

    def draw_xz_polygon(self, y, x1, z1, x2, z2):
        glBegin(GL_QUADS)
        glVertex3f(x1, self.f.y, self.f.z1)
        glVertex3f(x1, self.f.y, self.f.z2)
        glVertex3f(x2, self.f.y, self.f.z2)
        glVertex3f(x2, self.f.y, self.f.z1)
        glEnd()

    def draw_xy_polygon(self, z, x1, y1, x2, y2):
        glBegin(GL_QUADS)
        glVertex3f(x1, y1, z)
        glVertex3f(x1, y2, z)
        glVertex3f(x2, y2, z)
        glVertex3f(x2, y1, z)
        glEnd()

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.departure_position = None
        self.smoothed_branching_position = Smoother()
        self.segments = {}
        hue = random.uniform(0, 1)
        self.color = Vector3d(*(colorsys.hsv_to_rgb(hue, 0.35, 1)))
        self.position = Vector2d(random.uniform(0, NUM_STEPS * STEP_DEPTH), WALL_TOP)

    def add_segment(self, segment):
        if self.departure_position is None:
            self.departure_position = segment.departure_position
        segment.peer = self
        segment.gathered = False
        self.segments[segment.id] = segment

    def update(self):
        for segment in self.segments.values():
            if not segment.gathered and not segment.is_playing():
                segment.f.gatherer.add(segment)
                segment.gathered = True

        outdated = filter(lambda segment_id: self.segments[segment_id].outdated(),
                          self.segments)
        for segment_id in outdated:
            segment = self.segments[segment_id]
            del self.segments[segment_id]
        self.update_branching_position()

    def update_branching_position(self):
        if len(self.segments) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([segment.target_position() for segment in self.segments.values()]) / \
                len(self.segments)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(
                new_branching_position, self.visualizer.time_increment)

    def draw(self):
        if len(self.segments) > 0:
            for segment in self.segments.values():
                segment.draw_playing()
            for segment in self.segments.values():
                self.set_color(0)
                segment.draw_curve()

    def set_color(self, relative_age):
        glColor3f(1 - CURVE_OPACITY,
                  1 - CURVE_OPACITY,
                  1 - CURVE_OPACITY)

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.gatherer = Gatherer()
        self.y = self.visualizer.step_y(self.filenum+1)
        self.z1 = self.visualizer.step_z(self.filenum)
        self.z2 = self.visualizer.step_z(self.filenum+1)
        self.z = (self.z1 + self.z2) / 2
        self.neighbour_y = self.visualizer.step_y(self.filenum+2)
        self.neighbour_z1 = self.visualizer.step_z(self.filenum+1)

    def add_segment(self, segment):
        segment.departure_position = segment.peer.position
        self.visualizer.playing_segment(segment)

    def render(self):
        self.draw_gathered_segments()

    def draw_gathered_segments(self):
        for segment in self.gatherer.pieces():
            segment.draw_gathered()

    def byte_to_x(self, byte):
        return WALL_X + float(byte) / self.length * STAIRS_WIDTH


class Stairs(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer,
                                       segment_class=Segment)
        self.inner_x = WALL_X
        self.outer_x = WALL_X + STAIRS_WIDTH
        self.wall_rear_x = WALL_X - WALL_WIDTH
        self.wall_bottom = self.step_y(NUM_STEPS) - STEP_HEIGHT
        self.stairs_depth = self.step_z(NUM_STEPS)
        self.files = {}
        self.segments = {}
        self._dragging_orientation = False
        self._dragging_y_position = False
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self.enable_accum()
        self.enable_3d()

    def pan_segment(self, segment):
        x = WALL_X + STAIRS_WIDTH/2
        self.place_segment(segment.id,
                           segment.f.z, x,
                           segment.duration)

    def render(self):
        for peer in self.peers.values():
            peer.update()
        self.accum(self.render_accum_objects)
        if len(self.files) > 0:
            self.draw_branches()

    def render_accum_objects(self):
        self.draw_step_surfaces()
        self.draw_wall_surfaces()
        if len(self.files) > 0:
            self.draw_gathered_segments()

    def draw_branches(self):
        for peer in self.peers.values():
            peer.draw()

    def draw_step_surfaces(self):
        self.draw_step_horizontal_surfaces()
        self.draw_step_vertical_surfaces()

    def draw_step_horizontal_surfaces(self):
        glColor3f(*STEPS_COLOR_H)
        glBegin(GL_QUADS)
        for n in range(0, NUM_STEPS):
            surface = self.step_h_surface(n)
            for vertex in surface:
                glVertex3f(*vertex)
        glEnd()

    def draw_step_vertical_surfaces(self):
        glColor3f(*STEPS_COLOR_V)
        glBegin(GL_QUADS)
        for n in range(1, NUM_STEPS+1):
            surface = self.step_v_surface(n)
            for vertex in surface:
                glVertex3f(*vertex)
        glEnd()

    def draw_wall_surfaces(self):
        glColor3f(*WALL_COLOR_H)
        glBegin(GL_QUADS)
        glVertex3f(self.inner_x, WALL_TOP, 0)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, 0)
        glEnd()

        glColor3f(*WALL_COLOR_V)
        glBegin(GL_QUADS)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, self.wall_bottom, self.stairs_depth)
        glVertex3f(self.inner_x, self.wall_bottom, self.stairs_depth)
        glEnd()

    def step_h_surface(self, n):
        y1 = self.step_y(n)
        y2 = self.step_y(n+1)
        
        z1 = self.step_z(n)
        z2 = self.step_z(n+1)

        return [
            Vector3d(self.inner_x, y2, z1),
            Vector3d(self.inner_x, y2, z2),
            Vector3d(self.outer_x, y2, z2),
            Vector3d(self.outer_x, y2, z1)
            ]

    def step_v_surface(self, n):
        y1 = self.step_y(n)
        y2 = self.step_y(n+1)
        
        z1 = self.step_z(n)
        z2 = self.step_z(n+1)

        return [
            Vector3d(self.inner_x, y1, z1),
            Vector3d(self.inner_x, y2, z1),
            Vector3d(self.outer_x, y2, z1),
            Vector3d(self.outer_x, y1, z1)
            ]

    def step_y(self, step):
        return -step * STEP_HEIGHT

    def step_z(self, step):
        return step * STEP_DEPTH

    def draw_gathered_segments(self):
        for f in self.files.values():
            f.render()

if __name__ == '__main__':
    visualizer.run(Stairs)
