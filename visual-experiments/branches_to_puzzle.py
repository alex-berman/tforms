import visualizer
from gatherer import Gatherer
from OpenGL.GL import *
from collections import OrderedDict
from dynamic_scope import DynamicScope
import random
import time
from vector import Vector2d
from bezier import make_bezier

ARRIVAL_SIZE = 10
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05
MAX_BRANCH_AGE = 2.0
BRANCH_SUSTAIN = 1.5
ARRIVED_HEIGHT = 5
ARRIVED_OPACITY = 0.5
CURVE_PRECISION = 50
GREYSCALE = True

class Branch:
    def __init__(self, filenum, file_length, peer):
        self.filenum = filenum
        self.file_length = file_length
        self.peer = peer
        self.visualizer = peer.visualizer
        self.f = self.visualizer.files[filenum]
        self.playing_segments = OrderedDict()

    def add_segment(self, segment):
        self.playing_segments[segment.id] = segment
        self.cursor = segment.end
        self.last_updated = time.time()

    def age(self):
        return self.visualizer.now - self.last_updated

    def target_position(self):
        x = self.f.byte_to_coord(self.cursor)
        y = self.visualizer.filenum_to_y_coord(self.filenum) + ARRIVED_HEIGHT/2
        return Vector2d(x, y)

    def update(self):
        for segment in self.playing_segments.values():
            age = self.visualizer.now - segment.arrival_time
            if age > segment.duration:
                del self.playing_segments[segment.id]

    def draw_playing_segments(self):
        if len(self.playing_segments) > 0:
            segments_list = list(self.playing_segments.values())
            y = self.visualizer.filenum_to_y_coord(self.filenum)
            y1 = int(y)
            y2 = int(y + ARRIVED_HEIGHT) - 1
            x1 = int(self.f.byte_to_coord(segments_list[0].begin))
            x2 = int(self.f.byte_to_coord(segments_list[-1].end))
            if x2 == x1:
                x2 = x1 + 1
            glBegin(GL_QUADS)
            glColor3f(1,1,1)
            glVertex2i(x1, y2)
            glVertex2i(x1, y1)
            glColor3f(1,0,0)
            glVertex2i(x2, y1)
            glVertex2i(x2, y2)
            glEnd()

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        self.departure_position = None
        self.smoothed_branching_position = Smoother()
        self.branches = {}
        self.branch_count = 0
        self.hue = random.uniform(0, 1)

    def add_segment(self, segment):
        if self.departure_position is None:
            self.departure_position = segment.departure_position
        segment.peer = self
        branch = self.find_branch(segment)
        if not branch:
            branch = Branch(segment.filenum, segment.f.length, self)
            self.branches[self.branch_count] = branch
            self.branch_count += 1
        branch.add_segment(segment)

    def find_branch(self, segment):
        for branch in self.branches.values():
            if branch.filenum == segment.filenum and branch.cursor == segment.begin:
                return branch

    def update(self):
        outdated = filter(lambda branch_id:
                              self.branches[branch_id].age() > MAX_BRANCH_AGE,
                          self.branches)
        for branch_id in outdated:
            del self.branches[branch_id]
        self.update_branching_position()

        for branch in self.branches.values():
            branch.update()

    def update_branching_position(self):
        if len(self.branches) == 0:
            self.smoothed_branching_position.reset()
        else:
            average_target_position = \
                sum([branch.target_position() for branch in self.branches.values()]) / \
                len(self.branches)
            new_branching_position = self.departure_position*0.4 + average_target_position*0.6
            self.smoothed_branching_position.smooth(
                new_branching_position, self.visualizer.time_increment)

    def draw(self):
        if len(self.branches) > 0:
            glLineWidth(1.0)
            glEnable(GL_LINE_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            for branch in self.branches.values():
                self.set_color(0)
                self.draw_curve(branch)
                branch.draw_playing_segments()
            glDisable(GL_LINE_SMOOTH)
            glDisable(GL_BLEND)

    def set_color(self, relative_age):
        if GREYSCALE:
            glColor3f(0,0,0)
        else:
            color = colorsys.hsv_to_rgb(self.hue, 0.35, 1)
            glColor3f(relative_age + color[0] * (1-relative_age),
                      relative_age + color[1] * (1-relative_age),
                      relative_age + color[2] * (1-relative_age))

    def draw_line(self, p, q):
        glBegin(GL_LINES)
        glVertex2f(p.x, p.y)
        glVertex2f(q.x, q.y)
        glEnd()

    def draw_curve(self, branch):
        points = []
        branching_position = self.smoothed_branching_position.value()
        for i in range(15):
            points.append(self.departure_position * (1-i/14.0)+
                          branching_position * i/14.0)
        if branch.age() < BRANCH_SUSTAIN:
            target = branch.target_position()
        else:
            target = branching_position + (branch.target_position() - branching_position) * \
                (1 - (branch.age() - BRANCH_SUSTAIN) / (MAX_BRANCH_AGE - BRANCH_SUSTAIN))
        points.append(target)
        bezier = make_bezier([(p.x, p.y) for p in points])
        points = bezier(CURVE_PRECISION)
        glBegin(GL_LINE_STRIP)
        for x,y in points:
            glVertex2f(x, y)
        glEnd()
        if branch.age() < BRANCH_SUSTAIN:
            self.draw_line(Vector2d(target.x, target.y-ARRIVED_HEIGHT/2),
                           Vector2d(target.x, target.y+ARRIVED_HEIGHT/2))

class Smoother:
    RESPONSE_FACTOR = 5

    def __init__(self):
        self._current_value = None

    def smooth(self, new_value, time_increment):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * \
                self.RESPONSE_FACTOR * time_increment
        else:
            self._current_value = new_value

    def value(self):
        return self._current_value

    def reset(self):
        self._current_value = None

class File(visualizer.File):
    def __init__(self, *args):
        visualizer.File.__init__(self, *args)
        self.gatherer = Gatherer()
        self.x_scope = DynamicScope()

    def add_segment(self, segment):
        self.x_scope.put(segment.begin)
        self.x_scope.put(segment.end)
        segment.pan = (self.x_scope.map(segment.begin) + self.x_scope.map(segment.end)) / 2
        segment.departure_position = segment.peer_position()
        self.gatherer.add(segment)
        self.visualizer.playing_segment(segment, segment.pan)

    def render(self):
        self.x_scope.update()
        self.y = self.visualizer.filenum_to_y_coord(self.filenum)
        self.draw_gathered_segments()

    def draw_gathered_segments(self):
        opacity = ARRIVED_OPACITY
        glColor3f(1-opacity, 1-opacity, 1-opacity)
        for segment in self.gatherer.pieces():
            self.draw_segment(segment)

    def draw_segment(self, segment):
        y1 = int(self.y)
        y2 = int(self.y + ARRIVED_HEIGHT)
        x1 = int(self.byte_to_coord(segment.begin))
        x2 = int(self.byte_to_coord(segment.end))
        if x2 == x1:
            x2 = x1 + 1
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def byte_to_coord(self, byte):
        return self.visualizer.prepend_margin_width + \
            self.x_scope.map(byte) * self.visualizer.safe_width

class Puzzle(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer)
        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self.segments = {}
        self.y_scope = DynamicScope(padding=1)

    def render(self):
        if len(self.files) > 0:
            self.y_scope.update()
            self.draw_segments()
            self.draw_branches()

    def draw_branches(self):
        for peer in self.peers.values():
            peer.update()
            peer.draw()

    def draw_segments(self):
        for f in self.files.values():
            f.render()

    def added_file(self, f):
        self.y_scope.put(f.filenum)

    def filenum_to_y_coord(self, filenum):
        return self.y_scope.map(filenum) * self.height

if __name__ == '__main__':
    visualizer.run(Puzzle)
