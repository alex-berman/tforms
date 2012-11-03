from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys, os
import argparse
import collections
import logging
import math

dirname = os.path.dirname(__file__)
if dirname:
    sys.path.append(dirname + "/..")
else:
    sys.path.append("..")
from orchestra import VISUALIZER_PORT
from synth_controller import SynthController
from orchestra_controller import OrchestraController
from osc_receiver import OscReceiver
from stopwatch import Stopwatch
from ssr.ssr_control import SsrControl
from space import Space

logging.basicConfig(filename="visualizer.log", 
                    level=logging.DEBUG, 
                    filemode="w")

ESCAPE = '\033'
MARGIN = 30
BORDER_OPACITY = 0.7
FAKE_CHUNK_DURATION = 0.1
EXPORT_DIR = "export"

CAMERA_KEY_SPEED = 0.5
CAMERA_Y_SPEED = .1

NUM_ACCUM_SAMPLES = 8
ACCUM_JITTER = [
	(-0.334818,  0.435331),
	( 0.286438, -0.393495),
	( 0.459462,  0.141540),
	(-0.414498, -0.192829),
	(-0.183790,  0.082102),
	(-0.079263, -0.317383),
	( 0.102254,  0.299133),
	( 0.164216, -0.054399)
]

class File:
    def __init__(self, visualizer, filenum, offset, length):
        self.visualizer = visualizer
        self.filenum = filenum
        self.offset = offset
        self.length = length

    def add_chunk(self, chunk):
        pass

    def add_segment(self, segment):
        pass

class Chunk:
    def __init__(self, chunk_id, begin, end, byte_size,
                 filenum, peer_id,
                 arrival_time, visualizer):
        self.id = chunk_id
        self.begin = begin
        self.end = end
        self.byte_size = byte_size
        self.filenum = filenum
        self.peer_id = peer_id
        self.arrival_time = arrival_time
        self.visualizer = visualizer
        self.playing = False
        self.duration = FAKE_CHUNK_DURATION
        self.last_updated = visualizer.current_time()

    def append(self, other):
        self.end = other.end
        self.byte_size = self.end - self.begin
        self.last_updated = self.visualizer.current_time()

    def prepend(self, other):
        self.begin = other.begin
        self.byte_size = self.end - self.begin
        self.last_updated = self.visualizer.current_time()

    def joinable_with(self, other):
        return True

    def age(self):
        return self.visualizer.current_time() - self.arrival_time

    def relative_age(self):
        return self.age() / self.duration

    def is_playing(self):
        return self.relative_age() < 1

    def __str__(self):
        return "Chunk(id=%s, begin=%s, end=%s, filenum=%s)" % (
            self.id, self.begin, self.end, self.filenum)

class Segment(Chunk):
    def __init__(self, chunk_id, begin, end, byte_size,
                 filenum, f, peer_id, duration,
                 arrival_time, visualizer):
        Chunk.__init__(self, chunk_id, begin, end, byte_size,
                 filenum, peer_id,
                 arrival_time, visualizer)
        self.duration = duration
        self.f = f
        self.torrent_begin = self.begin + f.offset
        self.torrent_end = self.end + f.offset

    def playback_byte_cursor(self):
        return self.begin + min(self.relative_age(), 1) * self.byte_size

    def playback_torrent_byte_cursor(self):
        return self.torrent_begin + min(self.relative_age(), 1) * self.byte_size

    def append(self, other):
        Chunk.append(self, other)
        self.torrent_end = other.torrent_end

    def prepend(self, other):
        Chunk.prepend(self, other)
        self.torrent_begin = other.torrent_begin

    def __str__(self):
        return "Segment(id=%s, begin=%s, end=%s, filenum=%s, duration=%s)" % (
            self.id, self.begin, self.end, self.filenum, self.duration)

class Peer:
    def __init__(self, visualizer):
        self.visualizer = visualizer

    def add_segment(self, segment):
        pass

class Visualizer:
    def __init__(self, args,
                 file_class=File,
                 chunk_class=Chunk,
                 segment_class=Segment,
                 peer_class=Peer):
        self.file_class = file_class
        self.chunk_class = chunk_class
        self.segment_class = segment_class
        self.peer_class = peer_class
        self.sync = args.sync
        self.width = args.width
        self.height = args.height
        self.show_fps = args.show_fps
        self.export = args.export
        self.osc_log = args.osc_log
        self.ssr_enabled = args.ssr_enabled
        self.waveform_gain = args.waveform_gain
        self.logger = logging.getLogger("visualizer")
        self.files = {}
        self.peers = {}
        self.first_frame = True
        self.synth = SynthController()
        self.exiting = False
        self.time_increment = 0
        self.stopwatch = Stopwatch()
        self.space = Space()
        self._segments_by_id = {}
        self._warned_about_missing_pan_segment = False
        self.gl_display_mode = GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH
        self._3d_enabled = False
        self.torrent_length = 0

        if self.ssr_enabled:
            self.ssr = SsrControl()
        else:
            self.ssr = None

        if self.show_fps:
            self.fps_history = collections.deque(maxlen=10)
            self.previous_shown_fps_time = None

        self.setup_osc(self.osc_log)
        self.orchestra.register()

        if self.export:
            self.export_fps = args.export_fps
            from exporter import Exporter
            import shutil
            shutil.rmtree(EXPORT_DIR)
            os.mkdir(EXPORT_DIR)
            self.exporter = Exporter(EXPORT_DIR, MARGIN, MARGIN, self.width, self.height)

    def enable_3d(self):
        self._3d_enabled = True

    def run(self):
        window_width = self.width + MARGIN*2
        window_height = self.height + MARGIN*2
        glutInit(sys.argv)
        glutInitDisplayMode(self.gl_display_mode)
        glutInitWindowSize(window_width, window_height)
        glutInitWindowPosition(0, 0)
        glutCreateWindow("")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL()
        self.ReSizeGLScene(window_width, window_height)
        glutMainLoop()

    def handle_torrent_message(self, path, args, types, src, data):
        self.num_files = args[0]

    def handle_file_message(self, path, args, types, src, data):
        (filenum, offset, length) = args
        f = self.files[filenum] = self.file_class(self, filenum, offset, length)
        self.torrent_length += length
        self.added_file(f)
        if len(self.files) == self.num_files:
            self.added_all_files()

    def handle_chunk_message(self, path, args, types, src, data):
        (chunk_id, torrent_position, byte_size, filenum, peer_id) = args
        if filenum in self.files:
            begin = torrent_position - self.files[filenum].offset
            end = begin + byte_size
            chunk = self.chunk_class(
                chunk_id, begin, end, byte_size, filenum,
                peer_id, self.current_time(), self)
            self.files[filenum].add_chunk(chunk)
        else:
            print "ignoring chunk from undeclared file %s" % filenum

    def handle_segment_message(self, path, args, types, src, data):
        (segment_id, torrent_position, byte_size, filenum,
         peer_id, duration) = args
        if filenum in self.files:
            f = self.files[filenum]
            begin = torrent_position - f.offset
            end = begin + byte_size
            segment = self.segment_class(
                segment_id, begin, end, byte_size, filenum, f,
                peer_id, duration, self.current_time(), self)
            self._segments_by_id[segment_id] = segment

            self.add_segment(segment)
        else:
            print "ignoring segment from undeclared file %s" % filenum

    def handle_stopped_playing_segment_message(self, path, args, types, src, data):
        segment_id = args[0]
        segment = self._segments_by_id[segment_id]
        self.stopped_playing_segment(segment)

    def add_segment(self, segment):
        if not segment.peer_id in self.peers:
            self.peers[segment.peer_id] = self.peer_class(self)
        peer = self.peers[segment.peer_id]
        segment.peer = peer

        if self.ssr_enabled:
            segment.sound_source_id = self.ssr.allocate_source()
            if not segment.sound_source_id:
                print "WARNING: max sources exceeded, skipping segment playback"
        else:
            segment.sound_source_id = None
            
        f = self.files[segment.filenum]
        segment.f = f
        f.add_segment(segment)

        if segment.sound_source_id:
            self.pan_segment(segment)

        peer.add_segment(segment)

    def added_file(self, f):
        pass

    def added_all_files(self):
        pass

    def pan_segment(self, segment):
        if not self._warned_about_missing_pan_segment:
            print "WARNING: pan_segment undefined. All sounds will be centered."
            self._warned_about_missing_pan_segment = True

    def stopped_playing_segment(self, segment):
        if self.ssr_enabled and segment.sound_source_id:
            self.ssr.free_source(segment.sound_source_id)

    def handle_shutdown(self, path, args, types, src, data):
        self.exiting = True

    def handle_amp_message(self, path, args, types, src, data):
        (segment_id, amp) = args
        segment = self._segments_by_id[segment_id]
        self.handle_segment_amplitude(segment, amp)

    def handle_segment_amplitude(self, segment, amp):
        pass

    def handle_waveform_message(self, path, args, types, src, data):
        (segment_id, value) = args
        segment = self._segments_by_id[segment_id]
        self.handle_segment_waveform_value(segment, value * self.waveform_gain)

    def handle_segment_waveform_value(self, segment, value):
        pass

    def setup_osc(self, log_filename):
        self.orchestra = OrchestraController()
        self.server = OscReceiver(VISUALIZER_PORT, log_filename)
        self.server.add_method("/torrent", "i", self.handle_torrent_message)
        self.server.add_method("/file", "iii", self.handle_file_message)
        self.server.add_method("/chunk", "iiiii", self.handle_chunk_message)
        self.server.add_method("/segment", "iiiiif", self.handle_segment_message)
        self.server.add_method("/stopped_playing_segment", "i", self.handle_stopped_playing_segment_message)
        self.server.add_method("/shutdown", "", self.handle_shutdown)
        self.server.add_method("/amp", "if", self.handle_amp_message)
        self.server.add_method("/waveform", "if", self.handle_waveform_message)
        self.server.start()

    def InitGL(self):
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClearAccum(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glShadeModel(GL_SMOOTH)
        glutMouseFunc(self._mouse_clicked)
        glutMotionFunc(self._mouse_moved)
        glutSpecialFunc(self._special_key_pressed)

    def ReSizeGLScene(self, _width, _height):
        if _height == 0:
            _height = 1
        glViewport(0, 0, _width, _height)
        self._window_width = _width
        self._window_height = _height
        self._aspect_ratio = float(_width) / _height
        if not self._3d_enabled:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0.0, _width, _height, 0.0, -1.0, 1.0)
            glMatrixMode(GL_MODELVIEW)

    def DrawGLScene(self):
        if self.exiting:
            sys.exit()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if self.export:
            self.current_export_time = float(self.exporter.frame_count) / self.export_fps

        self.now = self.current_time()
        if self.first_frame:
            self.stopwatch.start()
            if self.sync:
                self.synth.sync_beep()
            self.first_frame = False
        else:
            self.time_increment = self.now - self.previous_frame_time
            glTranslatef(MARGIN, MARGIN, 0)
            self.draw_border()
            self.handle_incoming_messages()
            self.render()
            if self.show_fps:
                self.update_fps_history()
                self.show_fps_if_timely()

        glutSwapBuffers()
        self.previous_frame_time = self.now
        if self.export:
            self.exporter.export_frame()

    def handle_incoming_messages(self):
        if self.osc_log:
            self.server.serve_from_log_until(self.now)
        else:
            self.server.serve()

    def update_fps_history(self):
        fps = 1.0 / self.time_increment
        self.fps_history.append(fps)

    def show_fps_if_timely(self):
        if self.previous_shown_fps_time:
            if (self.now - self.previous_shown_fps_time) > 1.0:
                self.calculate_and_show_fps()
        else:
            self.calculate_and_show_fps()

    def calculate_and_show_fps(self):
        print sum(self.fps_history) / len(self.fps_history)
        self.previous_shown_fps_time = self.now

    def draw_border(self):
        x1 = y1 = -1
        x2 = self.width
        y2 = self.height
        glLineWidth(1)
        glColor3f(BORDER_OPACITY, BORDER_OPACITY, BORDER_OPACITY)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def keyPressed(self, *args):
        if args[0] == ESCAPE:
            self.synth.stop_all()
            self.exiting = True

    def playing_segment(self, segment):
        if segment.sound_source_id:
            channel = segment.sound_source_id - 1
            self.orchestra.visualizing_segment(segment.id, channel)
        segment.playing = True

    def current_time(self):
        if self.export:
            return self.current_export_time
        else:
            return self.stopwatch.get_elapsed_time()

    def set_color(self, color_vector, alpha=1.0):
        glColor4f(color_vector[0],
                  color_vector[1],
                  color_vector[2],
                  alpha)

    def set_listener_position(self, x, y):
        if self.ssr_enabled:
            self.ssr.set_listener_position(x, y)

    def set_listener_orientation(self, orientation):
        if self.ssr_enabled:
            self.ssr.set_listener_orientation(-orientation)

    def place_source(self, source_id, x, y, duration):
        if self.ssr_enabled:
            self.ssr.place_source(source_id, -x, y, duration)

    def _mouse_clicked(self, button, state, x, y):
        if button == GLUT_LEFT_BUTTON:
            self._dragging_orientation = (state == GLUT_DOWN)
        elif button == GLUT_RIGHT_BUTTON:
            self._dragging_y_position = (state == GLUT_DOWN)
        if state == GLUT_DOWN:
            self._drag_x_previous = x
            self._drag_y_previous = y

    def _mouse_moved(self, x, y):
        if self._dragging_orientation:
            self._set_camera_orientation(
                self._camera_y_orientation + x - self._drag_x_previous,
                self._camera_x_orientation - y + self._drag_y_previous)
            self._print_camera_settings()
        elif self._dragging_y_position:
            self._camera_position.y += CAMERA_Y_SPEED * (y - self._drag_y_previous)
            self._print_camera_settings()
        self._drag_x_previous = x
        self._drag_y_previous = y

    def _special_key_pressed(self, key, x, y):
        r = math.radians(self._camera_y_orientation)
        new_position = self._camera_position
        if key == GLUT_KEY_LEFT:
            new_position.x += CAMERA_KEY_SPEED * math.cos(r)
            new_position.z += CAMERA_KEY_SPEED * math.sin(r)
        elif key == GLUT_KEY_RIGHT:
            new_position.x -= CAMERA_KEY_SPEED * math.cos(r)
            new_position.z -= CAMERA_KEY_SPEED * math.sin(r)
        elif key == GLUT_KEY_UP:
            new_position.x += CAMERA_KEY_SPEED * math.cos(r + math.pi/2)
            new_position.z += CAMERA_KEY_SPEED * math.sin(r + math.pi/2)
        elif key == GLUT_KEY_DOWN:
            new_position.x -= CAMERA_KEY_SPEED * math.cos(r + math.pi/2)
            new_position.z -= CAMERA_KEY_SPEED * math.sin(r + math.pi/2)
        self._set_camera_position(new_position)
        self._print_camera_settings()

    def _print_camera_settings(self):
        print
        print "CAMERA_POSITION = %s" % self._camera_position
        print "CAMERA_Y_ORIENTATION = %s" % self._camera_y_orientation
        print "CAMERA_X_ORIENTATION = %s" % self._camera_x_orientation

    def _set_camera_position(self, position):
        self._camera_position = position
        self.set_listener_position(position.z, position.x)

    def _set_camera_orientation(self, y_orientation, x_orientation):
        self._camera_y_orientation = y_orientation
        self._camera_x_orientation = x_orientation
        self.set_listener_orientation(y_orientation)

    def set_perspective(self,
                       pixdx, pixdy,
                       eyedx, eyedy, eyedz):
        assert self._3d_enabled
        fov2 = ((self.fovy*math.pi) / 180.0) / 2.0
        top = self.near * math.tan(fov2)
        bottom = -top
        right = top * self._aspect_ratio
        left = -right
        xwsize = right - left
        ywsize = top - bottom
        # dx = -(pixdx*xwsize/self._window_width + eyedx*self.near/focus)
        # dy = -(pixdy*ywsize/self._window_height + eyedy*self.near/focus)
        # I don't understand why this modification solved the problem (focus was 1.0)
        dx = -(pixdx*xwsize/self._window_width)
        dy = -(pixdy*ywsize/self._window_height)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum (left + dx, right + dx, bottom + dy, top + dy, self.near, self.far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glRotatef(self._camera_x_orientation, 1.0, 0.0, 0.0)
        glRotatef(self._camera_y_orientation, 0.0, 1.0, 0.0)
        glTranslatef(self._camera_position.x, self._camera_position.y, self._camera_position.z)

    def enable_accum(self):
        self.fovy = 45
        self.near = 0.1
        self.far = 100.0
        self.gl_display_mode |= GLUT_ACCUM

    def accum(self, render_method):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)

        for jitter in range(NUM_ACCUM_SAMPLES):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.set_perspective(ACCUM_JITTER[jitter][0], ACCUM_JITTER[jitter][1],
                                 -self._camera_position.x, -self._camera_position.y, self._camera_position.z)
            render_method()
            glAccum(GL_ACCUM, 1.0/NUM_ACCUM_SAMPLES)

        glAccum(GL_RETURN, 1.0)

    def subscribe_to_amp(self):
        self.synth.subscribe_to_amp(VISUALIZER_PORT)

    def subscribe_to_waveform(self):
        self.synth.subscribe_to_waveform(VISUALIZER_PORT)


def run(visualizer_class):
    print "Hit ESC key to quit."

    parser = argparse.ArgumentParser()
    parser.add_argument('-sync', action='store_true')
    parser.add_argument('-width', dest='width', type=int, default=640)
    parser.add_argument('-height', dest='height', type=int, default=480)
    parser.add_argument('-show-fps', dest='show_fps', action='store_true')
    parser.add_argument('-osc-log', dest='osc_log')
    parser.add_argument('-export', dest='export', action='store_true')
    parser.add_argument('-export-fps', dest='export_fps', default=30.0, type=float)
    parser.add_argument("-no-ssr", dest="ssr_enabled", action="store_false", default=True)
    parser.add_argument("-waveform-gain", dest="waveform_gain", default=1, type=float)
    args = parser.parse_args()

    visualizer_class(args).run()
