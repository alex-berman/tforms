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
import collections
import copy
import math

NUM_STEPS = 12
STAIRS_WIDTH = 1.5
STEP_HEIGHT = 0.15
STEP_DEPTH = 0.3
WALL_X = -0.5
WALL_TOP = 2
WALL_WIDTH = 0.15
WAVEFORM_WIDTH = .05
WAVEFORM_THICKNESS = 2.0
WAVEFORM_ALONG_X = True
WAVEFORM_ALONG_WALL = True
WAVEFORM_SIZE = 60
WAVEFORM_LENGTH = STAIRS_WIDTH + 0.3

CONTROL_POINTS_BEFORE_BRANCH = 15
CURVE_PRECISION_ON_WALL = 50
RELATIVE_BRANCHING_POSITION = .4
CURVE_OPACITY = 0.8
SEGMENT_DECAY_TIME = 1.0
CURSOR_COLOR_V = Vector3d(.9, 0, 0)
CURSOR_COLOR_H = Vector3d(1, 0, 0)
STEPS_COLOR_V = WALL_SHADE_COLOR_V = Vector3d(.58, .58, .58)
STEPS_COLOR_H = WALL_SHADE_COLOR_H = Vector3d(.9, .9, .9)
WALL_COLOR = (1.0, 1.0, 1.0)
GATHERED_OPACITY = .3
CURSOR_THICKNESS = 2.0
GATHERED_COLOR_V = Vector3d(.62, .17, .20)
GATHERED_COLOR_H = Vector3d(.9, .3, .35)

# CAMERA_POSITION = Vector3d(-4.6, -0.6, -8.6)
# CAMERA_Y_ORIENTATION = -37
# CAMERA_X_ORIENTATION = 0

# CAMERA_POSITION = Vector(3, [-4.4240142191185345, -2.9, -6.754711866271528])
# CAMERA_Y_ORIENTATION = -42
# CAMERA_X_ORIENTATION = 25

# CAMERA_POSITION = Vector(3, [-3.0857530064008176, -0.8999999999999985, -5.26842221531674])
# CAMERA_Y_ORIENTATION = -42
# CAMERA_X_ORIENTATION = 25

CAMERA_POSITION = Vector(3, [-5.516145180239982, -0.599999999999998, -1.9135947601016645])
CAMERA_Y_ORIENTATION = -88
CAMERA_X_ORIENTATION = 9

def clamp(value, min_value, max_value):
    return max(min(max_value, value), min_value)


class Segment(visualizer.Segment):
    HALF_PI = math.pi/2

    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.step = self.visualizer._byte_to_step(self.torrent_begin)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0

    def target_position(self):
        return self.wall_step_crossing()

    def wall_step_crossing(self):
        if WAVEFORM_ALONG_X:
            if self.peer.departure_position[0] > self.step.z1:
                z = self.step.z1 + STEP_DEPTH * self.playback_byte_cursor() / self.f.length
            else:
                z = self.step.z2 - STEP_DEPTH * self.playback_byte_cursor() / self.f.length
            return Vector2d(z, self.step.y)
        else:
            return Vector2d(self.step.z2, self.step.y)

    def decay_time(self):
        return self.age() - self.duration

    def outdated(self):
        return (self.age() - self.duration) > SEGMENT_DECAY_TIME

    def draw_curve(self):
        curve = self.curve_on_wall()
        if self.visualizer.args.waveform and \
                WAVEFORM_ALONG_WALL and \
                self.is_playing():
            curve = self._stretch_curve_with_waveform(curve)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glLineWidth(2)
        glBegin(GL_LINE_STRIP)
        for z,y in curve:
            glVertex3f(WALL_X, y, z)
        glEnd()

    def _stretch_curve_with_waveform(self, curve):
        vertex_for_waveform_start = self._vertex_for_waveform_start(curve)
        num_waveform_vertices = CURVE_PRECISION_ON_WALL - vertex_for_waveform_start
        result = curve[0:vertex_for_waveform_start]
        for n in range(num_waveform_vertices):
            relative_n = float(n) / num_waveform_vertices
            x1, y1 = curve[vertex_for_waveform_start + n - 1]
            x2, y2 = curve[vertex_for_waveform_start + n]
            bearing = math.atan2(y2 - y1, x2 - x1)
            stretch_angle = bearing + self.HALF_PI
            w = self.waveform[
                int(relative_n * self.waveform_frames_along_wall)]
            stretch = w * WAVEFORM_WIDTH * relative_n
            v = (x2 + stretch * math.cos(stretch_angle),
                 y2 + stretch * math.sin(stretch_angle))
            result.append(v)
        return result

    def _vertex_for_waveform_start(self, curve):
        waveform_length_on_wall = WAVEFORM_LENGTH - self.waveform_length_on_step
        result = 0
        length = 0
        for n in range(CURVE_PRECISION_ON_WALL - 1):
            x1, y1 = curve[n]
            x2, y2 = curve[n+1]
            dx = x2 - x1
            dy = y2 - y1
            length += math.sqrt(dx*dx + dy*dy)
            if length > waveform_length_on_wall:
                return result
            result += 1
        return result

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

    def draw_gathered(self):
        self.draw_as_gathered(self.torrent_begin, self.torrent_end)

    def draw_as_gathered(self, begin, end):
        x1 = self.step.byte_to_x(begin)
        x2 = self.step.byte_to_x(end)
        self.visualizer.set_color(self.visualizer.gathered_color_h)
        self.draw_xz_polygon(self.step.y,
                             x1, self.step.z1,
                             x2, self.step.z2)

        self.visualizer.set_color(self.visualizer.gathered_color_v)
        self.draw_xy_polygon(self.step.z2,
                             x1, self.step.y,
                             x2, self.step.neighbour_y)

    def draw_playing(self):
        if self.is_playing():
            if not self.visualizer.args.waveform:
                self.draw_as_gathered(self.torrent_begin, self.playback_torrent_byte_cursor())
            self.draw_cursor_and_waveform()

    def draw_cursor_and_waveform(self):
        self.cursor_x = self.step.byte_to_x(self.playback_torrent_byte_cursor())

        if self.visualizer.args.waveform:
            self.waveform_length_on_step = self.cursor_x - self.visualizer.inner_x
            self.waveform_frames_along_step = int(
                float(self.waveform_length_on_step) / WAVEFORM_LENGTH * WAVEFORM_SIZE)
            self.waveform_frames_along_wall = WAVEFORM_SIZE - self.waveform_frames_along_step
            amp = max([abs(value) for value in self.waveform])

            if WAVEFORM_ALONG_X:
                z = self.wall_step_crossing()[0]
                self.peer.set_color(0)
                self.draw_waveform_on_step_along_x(
                    z, self.step.y, self.visualizer.inner_x, self.cursor_x)
            else:
                self.visualizer.set_color(self.amp_controlled_color(
                    self.visualizer.gathered_color_h, CURSOR_COLOR_H, amp))
                self.draw_waveform_on_step_along_z(
                    self.cursor_x, self.step.y, self.step.z1, self.step.z2)
        else:
            amp = self.amp

        if not (self.visualizer.args.waveform and not WAVEFORM_ALONG_X):
            self.visualizer.set_color(
                self.amp_controlled_color(STEPS_COLOR_H, CURSOR_COLOR_H, amp))
            glLineWidth(CURSOR_THICKNESS)
            glBegin(GL_LINES)
            glVertex3f(self.cursor_x, self.step.y, self.step.z1)
            glVertex3f(self.cursor_x, self.step.y, self.step.z2)
            glEnd()

        glBegin(GL_LINES)
        self.visualizer.set_color(self.amp_controlled_color(
                self.visualizer.gathered_color_v, CURSOR_COLOR_V, amp))
        glVertex3f(self.cursor_x, self.step.y, self.step.z2)
        glVertex3f(self.cursor_x, self.step.neighbour_y, self.step.neighbour_z1)
        glEnd()

    def draw_waveform_on_step_along_x(self, z_baseline, y, x1, x2):
        glLineWidth(WAVEFORM_THICKNESS)
        glBegin(GL_LINE_STRIP)
        glVertex3f(x1, y, z_baseline)
        n = 0
        for waveform_frame in range(
            self.waveform_frames_along_wall,
            self.waveform_frames_along_wall + \
                self.waveform_frames_along_step):
            value = self.waveform[waveform_frame]
            x = x1 + (float(n) / self.waveform_frames_along_step) * (x2 - x1)
            z = clamp(z_baseline + value * WAVEFORM_WIDTH,
                      self.step.z1, self.step.z2)
            glVertex3f(x, y, z)
            n += 1
        glVertex3f(x2, y, z_baseline)
        glEnd()

    def draw_waveform_on_step_along_z(self, x_baseline, y, z1, z2):
        glLineWidth(WAVEFORM_THICKNESS)
        glBegin(GL_LINE_STRIP)
        glVertex3f(x_baseline, y, z1)
        n = 1
        for value in self.waveform:
            z = z1 + (float(n) / (len(self.waveform) + 1)) * (z2 - z1)
            x = clamp(x_baseline + value * WAVEFORM_WIDTH, 
                      self.visualizer.inner_x, self.visualizer.outer_x)
            glVertex3f(x, y, z)
            n += 1
        glVertex3f(x_baseline, y, z2)
        glEnd()

    def draw_xz_polygon(self, y, x1, z1, x2, z2):
        glBegin(GL_QUADS)
        glVertex3f(x1, self.step.y, self.step.z1)
        glVertex3f(x1, self.step.y, self.step.z2)
        glVertex3f(x2, self.step.y, self.step.z2)
        glVertex3f(x2, self.step.y, self.step.z1)
        glEnd()

    def draw_xy_polygon(self, z, x1, y1, x2, y2):
        glBegin(GL_QUADS)
        glVertex3f(x1, y1, z)
        glVertex3f(x1, y2, z)
        glVertex3f(x2, y2, z)
        glVertex3f(x2, y1, z)
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * amp

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
                self.visualizer.gather(segment)
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
            new_branching_position = self.departure_position * RELATIVE_BRANCHING_POSITION \
                + average_target_position * (1-RELATIVE_BRANCHING_POSITION)
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

class Step:
    def __init__(self, visualizer, n, byte_offset, byte_size):
        self.visualizer = visualizer
        self.n = n
        self.byte_offset = byte_offset
        self.byte_size = byte_size
        self.byte_end = byte_offset + byte_size
        self.y = visualizer.step_y(n+1)
        self.z1 = visualizer.step_z(n)
        self.z2 = visualizer.step_z(n+1)
        self.z = (self.z1 + self.z2) / 2
        self.neighbour_y = visualizer.step_y(n+2)
        self.neighbour_z1 = visualizer.step_z(n+1)

    def __repr__(self):
        return "Step(n=%s, byte_offset=%s, byte_end=%s)" % (self.n, self.byte_offset, self.byte_end)

    def byte_to_x(self, byte):
        return WALL_X + float(byte - self.byte_offset) / self.byte_size * STAIRS_WIDTH


class File(visualizer.File):
    def add_segment(self, segment):
        segment.departure_position = segment.peer.position
        self.visualizer.playing_segment(segment)


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
        self.gatherer = Gatherer()
        self._segments_split_at_step_boundaries = None
        self._dragging_orientation = False
        self._dragging_y_position = False
        self._set_camera_position(CAMERA_POSITION)
        self._set_camera_orientation(CAMERA_Y_ORIENTATION, CAMERA_X_ORIENTATION)
        self.enable_accum()
        self.enable_3d()
        if self.args.waveform:
            self.gathered_color_v = CURSOR_COLOR_V * GATHERED_OPACITY + STEPS_COLOR_V * (1 - GATHERED_OPACITY)
            self.gathered_color_h = CURSOR_COLOR_H * GATHERED_OPACITY + STEPS_COLOR_H * (1 - GATHERED_OPACITY)
            self.subscribe_to_waveform()
        else:
            self.gathered_color_v = GATHERED_COLOR_V
            self.gathered_color_h = GATHERED_COLOR_H
            self.subscribe_to_amp()

    def gather(self, segment):
        self.gatherer.add(segment)
        self._segments_split_at_step_boundaries = None

    def added_all_files(self):
        self._create_steps()

    def _create_steps(self):
        self._steps = []
        remaining_bytes = self.torrent_length
        remaining_num_steps = NUM_STEPS
        byte_offset = 0
        for n in range(NUM_STEPS):
            byte_size = int(remaining_bytes / remaining_num_steps)
            self._steps.append(Step(self, n, byte_offset, byte_size))
            byte_offset += byte_size
            remaining_bytes -= byte_size
            remaining_num_steps -= 1

    def pan_segment(self, segment):
        x = WALL_X + STAIRS_WIDTH/2
        self.place_segment(segment.id,
                           segment.step.z, x,
                           segment.duration)

    def render(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POLYGON_OFFSET_FILL)
        for peer in self.peers.values():
            peer.update()
        self.accum(self.render_accum_objects)
        if len(self.files) > 0:
            self.draw_branches()

        glDisable(GL_DEPTH_TEST)
        self.draw_step_edges()
        self.draw_wall_edge()

    def render_accum_objects(self):
        glPolygonOffset(1.0, 0.0)
        self.draw_step_surfaces()
        self.draw_wall_surfaces()
        if len(self.files) > 0:
            glPolygonOffset(0.0, 0.0)
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

    def draw_step_edges(self):
        glLineWidth(1.0)
        glColor3f(*STEPS_COLOR_V)
        for n in range(1, NUM_STEPS+1):
            y = self.step_y(n)
            z = self.step_z(n)
            glBegin(GL_LINES)
            glVertex3f(self.inner_x, y, z)
            glVertex3f(self.outer_x, y, z)
            glEnd()

    def draw_wall_edge(self):
        glLineWidth(1.0)
        glColor3f(*WALL_SHADE_COLOR_H)
        glBegin(GL_LINES)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.inner_x, self.wall_bottom, self.stairs_depth)
        glEnd()

    def draw_wall_surfaces(self):
        glColor3f(*WALL_SHADE_COLOR_H)
        glBegin(GL_QUADS)
        glVertex3f(self.inner_x, WALL_TOP, 0)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, 0)
        glEnd()

        glColor3f(*WALL_SHADE_COLOR_V)
        glBegin(GL_QUADS)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.wall_rear_x, self.wall_bottom, self.stairs_depth)
        glVertex3f(self.inner_x, self.wall_bottom, self.stairs_depth)
        glEnd()

        glColor3f(*WALL_COLOR)
        glBegin(GL_QUADS)
        glVertex3f(self.inner_x, WALL_TOP, 0)
        glVertex3f(self.inner_x, WALL_TOP, self.stairs_depth)
        glVertex3f(self.inner_x, self.wall_bottom, self.stairs_depth)
        glVertex3f(self.inner_x, self.wall_bottom, 0)
        glEnd()

        for n in range(1, NUM_STEPS+1):
            glBegin(GL_POLYGON)
            z = self.step_z(n)
            y1 = self.step_y(n)
            y2 = self.step_y(n+1)
            glVertex3f(self.outer_x, y1, z)
            glVertex3f(self.outer_x, y2, z)
            glVertex3f(self.outer_x, y2, 0)
            glVertex3f(self.outer_x, y1, 0)
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
        if self._segments_split_at_step_boundaries is None:
            self._segments_split_at_step_boundaries = self._split_segments_at_step_boundaries(
                self.gatherer.pieces())
        for segment in self._segments_split_at_step_boundaries:
            segment.draw_gathered()

    def _split_segments_at_step_boundaries(self, pieces):
        result = []
        for piece in pieces:
            segments = self._split_at_step_boundaries(piece)
            result.extend(segments)
        return result

    def _split_at_step_boundaries(self, segment):
        result = []
        for step in self._steps:
            if self._segment_matches_step(segment, step):
                new_segment = copy.copy(segment)
                new_segment.torrent_begin = max(segment.torrent_begin, step.byte_offset)
                new_segment.torrent_end = min(segment.torrent_end, step.byte_offset + step.byte_size)
                new_segment.step = step
                result.append(new_segment)
        return result

    def _segment_matches_step(self, segment, step):
        return (step.byte_offset <= segment.torrent_begin < (step.byte_offset + step.byte_size) or
                step.byte_offset < segment.torrent_end <= (step.byte_offset + step.byte_size))

    def _byte_to_step(self, byte):
        for step in self._steps:
            if step.byte_offset <= byte and byte < step.byte_end:
                return step
        raise Exception("failed to get step for byte %s with steps %s" % (byte, self._steps))

    def handle_segment_waveform_value(self, segment, value):
        segment.waveform.appendleft(value)

    def handle_segment_amplitude(self, segment, amp):
        segment.amp = amp

if __name__ == '__main__':
    visualizer.run(Stairs)
