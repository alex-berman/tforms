from argparse import ArgumentParser
import rectangular_visualizer as visualizer
import collections
from OpenGL.GL import *
from OpenGL.GLUT import *
from vector import Vector3d
from gatherer import Gatherer
from math_tools import sigmoid
import random

WAVEFORM_SIZE = 60
WAVEFORM_MAGNITUDE = 30.0 / 480
#GATHERED_COLOR = Vector3d(0.6, 0.2, 0.1)
GATHERED_COLOR = Vector3d(0.3, 0.3, 0.3)
WAVEFORM_COLOR = Vector3d(1.0, 1.0, 1.0)
GATHERED_LINE_WIDTH = 1.0 / 480
WAVEFORM_LINE_WIDTH = 3.0 / 480
MAX_GRADIENT_HEIGHT = 3.0 / 480
FADE_OUT_DURATION = 5.0
PEER_INFO_AMP_THRESHOLD = 0.1
PEER_INFO_FADE_IN = 1.0
PEER_INFO_FADE_OUT = 0.3

class Peer(visualizer.Peer):
    def __init__(self, *args):
        visualizer.Peer.__init__(self, *args)
        if self.pan < 0:
            self.side = "left"
        else:
            self.side = "right"

class Segment(visualizer.Segment):
    def __init__(self, *args):
        visualizer.Segment.__init__(self, *args)
        self.waveform = collections.deque([], maxlen=WAVEFORM_SIZE)
        self.waveform.extend([0.0] * WAVEFORM_SIZE)
        self.amp = 0
        self.pan = 0.5
        self.y = self.visualizer.byte_to_py(self.torrent_begin)
        if self.visualizer.args.peer_info:
            self._prepare_peer_info()

    def _prepare_peer_info(self):
        self._peer_info_renderer = PeerInfoRenderer(self.peer, self.y, self.visualizer)
        self._peer_info_size = self._peer_info_renderer.size()
        self._peer_info_fade_in = min(self.duration/2, PEER_INFO_FADE_IN)
        self._peer_info_fade_out = min(self.duration/2, PEER_INFO_FADE_IN)
        self._peer_info_allocation_id = None
            
    def render(self):
        self._amp = max([abs(value) for value in self.waveform])
        self._render_waveform()
        if self.visualizer.args.peer_info:
            self._potentially_render_peer_info()

    def _potentially_render_peer_info(self):
        if not self._peer_info_allocation_id and self._amp > PEER_INFO_AMP_THRESHOLD:
            self._try_allocate_place_for_peer_info()
        if self._peer_info_allocation_id:
            self._render_peer_info()

    def _try_allocate_place_for_peer_info(self):
        v_aligns = ["top", "bottom"]
        random.shuffle(v_aligns)
        h_aligns = set(["left", "right"])
        while len(h_aligns) > 0:
            if self.peer.side in h_aligns:
                h_align = self.peer.side
            else:
                h_align = random.choice(list(h_aligns))
            h_aligns.remove(h_align)

            for v_align in v_aligns:
                if self._try_allocate_place_for_peer_info_with_align(h_align, v_align):
                    self._peer_info_h_align = h_align
                    self._peer_info_v_align = v_align
                    return True

    def _try_allocate_place_for_peer_info_with_align(self, h_align, v_align):
        allocator = self.visualizer.allocators[h_align]
        width, height = self._peer_info_renderer.size()
        y1 = self._peer_info_renderer.v_position(v_align)
        y2 = y1 + height
        self._peer_info_allocation_id = allocator.allocate(y1, y2)
        if self._peer_info_allocation_id:
            return True

    def free(self):
        if self.visualizer.args.peer_info and self._peer_info_allocation_id:
            allocator = self.visualizer.allocators[self._peer_info_h_align]
            allocator.free(self._peer_info_allocation_id)

    def _render_peer_info(self):
        glColor4f(1,1,1, self._text_opacity())
        self._peer_info_renderer.render(
            self._peer_info_h_align,
            self._peer_info_v_align)

    def _render_waveform(self):
        glLineWidth(self.amp_controlled_line_width(
                GATHERED_LINE_WIDTH, WAVEFORM_LINE_WIDTH, self._amp))
        self.visualizer.set_color(self.amp_controlled_color(
                self.visualizer.gathered_color, WAVEFORM_COLOR, self._amp))

        glBegin(GL_LINE_STRIP)
        n = 0
        for value in self.waveform:
            x = n * self.visualizer.width / (WAVEFORM_SIZE-1)
            y = self.y + value * WAVEFORM_MAGNITUDE * self.visualizer.height
            glVertex2f(x, y)
            n += 1
        glEnd()

    def amp_controlled_color(self, weak_color, strong_color, amp):
        return weak_color + (strong_color - weak_color) * sigmoid(pow(amp, 0.25))

    def amp_controlled_line_width(self, weak_line_width, strong_line_width, amp):
        return (weak_line_width + (strong_line_width - weak_line_width) * pow(amp, 0.25)) * self.visualizer.height

    def _text_opacity(self):
        age = self.age()
        if age < self._peer_info_fade_in:
            return sigmoid(age / self._peer_info_fade_in)
        elif age > (self.duration - self._peer_info_fade_out):
            return 1 - sigmoid(1 - (self.duration - age) / self._peer_info_fade_out)
        else:
            return 1

class PeerInfoRenderer:
    def __init__(self, peer, y, visualizer):
        self.peer = peer
        self.visualizer = visualizer
        self._text = self._anonymize_addr(peer.addr)
        self._scale = 0.07 / 1024 * self.visualizer.width
        self._h_margin = 10.0 / 640 * self.visualizer.height
        self._v_margin = 10.0 / 640 * self.visualizer.height
        self.y = y - self._scale * 33.33

    def _anonymize_addr(self, addr):
        parts = addr.split(".")
        parts[-1] = self._anonymize_addr_part(parts[-1])
        return ".".join(parts)

    def _anonymize_addr_part(self, string):
        chars = list(string)
        chars[random.randint(0, len(chars)-1)] = "X"
        return "".join(chars)

    def render(self, h_align, v_align):
        glLineWidth(1.0)
        glPointSize(1.0)

        if h_align == "left":
            x = self._h_margin
        else:
            x = self.visualizer.width - self._h_margin

        self.visualizer.draw_text(
            text = self._text,
            scale = self._scale,
            x = x, y = self.v_position(v_align),
            font = GLUT_STROKE_MONO_ROMAN,
            h_align = h_align,
            v_align = v_align)

    def v_position(self, v_align):
        if v_align == "top":
            return self.y + self._v_margin
        else:
            return self.y - self._v_margin

    def size(self):
        return self.visualizer.get_text_size(
            text = self._text,
            scale = self._scale)

class File(visualizer.File):
    def add_segment(self, segment):
        self.visualizer.playing_segment(segment)
        self.visualizer.playing_segments[segment.id] = segment
        if segment.peer.side == "left":
            segment.append_to_waveform = segment.waveform.appendleft
        else:
            segment.append_to_waveform = segment.waveform.append

class Waves(visualizer.Visualizer):
    def __init__(self, args):
        self._gathered_segments_layer = None
        visualizer.Visualizer.__init__(self, args,
                                       file_class=File,
                                       peer_class=Peer,
                                       segment_class=Segment)
        if self.args.peer_info:
            self.allocators = {"left":  RasterAllocator(),
                               "right": RasterAllocator()}
        
    @staticmethod
    def add_parser_arguments(parser):
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("--peer-info", action="store_true")

    def configure_2d_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.window_width, 0.0, self.window_height, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)

    def synth_address_received(self):
        self.subscribe_to_waveform()

    def reset(self):
        visualizer.Visualizer.reset(self)
        self.playing_segments = collections.OrderedDict()
        self.gatherer = Gatherer()
        if self._gathered_segments_layer:
            self._gathered_segments_layer.refresh()

    def pan_segment(self, segment):
        # let orchestra & synth spatialize
        pass

    def InitGL(self):
        visualizer.Visualizer.InitGL(self)
        glClearColor(0.0, 0.0, 0.0, 0.0)
        self._gathered_segments_layer = self.new_layer(self._render_gathered_segments)

    def update(self):
        outdated = []
        for segment in self.playing_segments.values():
            if not segment.is_playing():
                self.gatherer.add(segment)
                outdated.append(segment.id)

        if len(outdated) > 0:
            for segment_id in outdated:
                self.playing_segments[segment_id].free()
                del self.playing_segments[segment_id]
            self._gathered_segments_layer.refresh()

    def render(self):
        self.update()
        self._set_gathered_color()
        self._gathered_segments_layer.draw()
        self.draw_playing_segments()

    def _set_gathered_color(self):
        if self.download_completed():
            time_after_completion = max(self.now - self.torrent_download_completion_time, 0)
            if time_after_completion > FADE_OUT_DURATION:
                self.gathered_color = Vector3d(0,0,0)
            else:
                self.gathered_color = WAVEFORM_COLOR * pow(1 - time_after_completion/FADE_OUT_DURATION, 0.15)
            self._gathered_segments_layer.refresh()
        elif self.torrent_length > 0:
            torrent_progress = float(self.gatherer.gathered_bytes()) / self.torrent_length
            self.gathered_color = GATHERED_COLOR + (WAVEFORM_COLOR - GATHERED_COLOR) * pow(torrent_progress, 20)
        else:
            self.gathered_color = GATHERED_COLOR

    def active(self):
        return len(self.playing_segments) > 0

    def finished(self):
        if self.download_completed():
            time_after_completion = max(self.now - self.torrent_download_completion_time, 0)
            if time_after_completion > FADE_OUT_DURATION:
                return True

    def draw_playing_segments(self):
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for segment in self.playing_segments.values():
            segment.render()

    def _render_gathered_segments(self):
        glBegin(GL_QUADS)
        x1 = 0
        x2 = self.width
        min_height = GATHERED_LINE_WIDTH * self.height
        for segment in self.gatherer.pieces():
            y1 = self.byte_to_py(segment.torrent_begin)
            y2 = max(self.byte_to_py(segment.torrent_end), y1 + min_height)
            if (y2 - y1) > min_height:
                d = min((y2 - y1) * 0.2, MAX_GRADIENT_HEIGHT * self.height)
                y1d = y1 + d
                y2d = y2 - d

                glColor3f(0, 0, 0)
                glVertex2f(x1, y1)

                glColor3f(*self.gathered_color)
                glVertex2f(x1, y1d)
                glVertex2f(x2, y1d)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y1)



                glColor3f(0, 0, 0)
                glVertex2f(x1, y2)

                glColor3f(*self.gathered_color)
                glVertex2f(x1, y2d)
                glVertex2f(x2, y2d)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y2)


                glColor3f(*self.gathered_color)
                glVertex2f(x1, y1d)
                glVertex2f(x1, y2d)
                glVertex2f(x2, y2d)
                glVertex2f(x2, y1d)
            else:
                glColor3f(0, 0, 0)
                glVertex2f(x1, y1)

                glColor3f(*self.gathered_color)
                glVertex2f(x1, y2)
                glVertex2f(x2, y2)

                glColor3f(0, 0, 0)
                glVertex2f(x2, y1)
        glEnd()

    def byte_to_py(self, byte):
        return int(self.byte_to_relative_y(byte) * self.height)

    def byte_to_relative_y(self, byte):
        return float(byte) / self.torrent_length

    def handle_segment_waveform_value(self, segment, value):
        segment.append_to_waveform(value)

class RasterAllocator:
    def __init__(self):
        self._allocations = {}
        self._id_count = 0

    def allocate(self, begin, end):
        for allocation in self._allocations.values():
            if self._overlap(allocation["begin"], allocation["end"], begin, end):
                return False
        allocation_id = self._id_count
        self._allocations[allocation_id] = {"begin": begin, "end": end}
        self._id_count += 1
        return allocation_id

    def _overlap(self, begin1, end1, begin2, end2):
        return ((begin2 <= begin1 <= end2) or
                (begin2 <= end1 <= end2) or
                (begin1 <= begin2 <= end1) or
                (begin1 <= end2 <= end1))

    def free(self, allocation_id):
        del self._allocations[allocation_id]

if __name__ == "__main__":
    parser = ArgumentParser()
    Waves.add_parser_arguments(parser)
    options = parser.parse_args()
    Waves(options).run()
