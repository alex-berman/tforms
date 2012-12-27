from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys, os
import argparse
import collections
import logging
import math
import liblo
from exporter import Exporter

dirname = os.path.dirname(__file__)
if dirname:
    sys.path.append(dirname + "/..")
else:
    sys.path.append("..")
from synth_controller import SynthController
from orchestra_controller import OrchestraController
from osc_receiver import OscReceiver
from stopwatch import Stopwatch
import traceback_printer
from camera_script_interpreter import CameraScriptInterpreter

logging.basicConfig(filename="visualizer.log", 
                    level=logging.DEBUG, 
                    filemode="w")

ESCAPE = '\033'
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

    def __str__(self):
        return "File(filenum=%s, offset=%s, length=%s)" % (
            self.filenum, self.offset, self.length)

class Chunk:
    def __init__(self, chunk_id, begin, end, byte_size,
                 filenum, f, peer_id, t,
                 arrival_time, visualizer):
        self.id = chunk_id
        self.begin = begin
        self.end = end
        self.byte_size = byte_size
        self.filenum = filenum
        self.f = f
        self.peer_id = peer_id
        self.t = t
        self.arrival_time = arrival_time
        self.visualizer = visualizer
        self.playing = False
        self.duration = FAKE_CHUNK_DURATION
        self.last_updated = visualizer.current_time()
        self.torrent_begin = self.begin + f.offset
        self.torrent_end = self.end + f.offset

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

    def __repr__(self):
        return "Chunk(id=%s, begin=%s, end=%s, filenum=%s)" % (
            self.id, self.begin, self.end, self.filenum)

class Segment(Chunk):
    def __init__(self, chunk_id, begin, end, byte_size,
                 filenum, f, peer_id, t, duration,
                 arrival_time, visualizer):
        Chunk.__init__(self, chunk_id, begin, end, byte_size,
                 filenum, f, peer_id, t,
                 arrival_time, visualizer)
        self.duration = duration

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

    def __repr__(self):
        return "Segment(id=%s, begin=%s, end=%s, torrent_begin=%s, torrent_end=%s, filenum=%s, duration=%s)" % (
            self.id, self.begin, self.end, self.torrent_begin, self.torrent_end, self.filenum, self.duration)

class Peer:
    def __init__(self, visualizer, addr, bearing):
        self.visualizer = visualizer
        self.addr = addr
        self.bearing = bearing

    def add_segment(self, segment):
        pass


class Layer:
    def __init__(self, rendering_function, display_list_id):
        self._rendering_function = rendering_function
        self._updated = False
        self._display_list_id = display_list_id

    def draw(self):
        if self._updated:
            glCallList(self._display_list_id)
        else:
            glNewList(self._display_list_id, GL_COMPILE_AND_EXECUTE)
            self._rendering_function()
            glEndList()
            self._updated = True

    def refresh(self):
        self._updated = False


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
        self.args = args
        self.sync = args.sync
        self.width = args.width
        self.height = args.height
        self.margin = args.margin
        self.show_fps = args.show_fps
        self.export = args.export
        self.osc_log = args.osc_log
        self.waveform_gain = args.waveform_gain
        self._standalone = args.standalone

        self.logger = logging.getLogger("visualizer")
        self.reset()
        self.first_frame = True
        self.synth = SynthController()
        self.exiting = False
        self.time_increment = 0
        self.stopwatch = Stopwatch()
        self._layers = []
        self._display_list_count = 0
        self._warned_about_missing_pan_segment = False
        self.gl_display_mode = GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH
        self._accum_enabled = False
        self._3d_enabled = False
        self.fovy = 45
        self.near = 0.1
        self.far = 100.0

        if args.camera_script:
            self._camera_script = CameraScriptInterpreter(args.camera_script)
        else:
            self._camera_script = None

        if self.show_fps:
            self.fps_history = collections.deque(maxlen=10)
            self.previous_shown_fps_time = None

        if not args.standalone:
            self.orchestra_port = args.port
            self.setup_osc(self.osc_log)
            self.orchestra.register(self.server.port)

        self._screen_dumper = Exporter(".", self.margin, self.margin, self.width, self.height)
        if self.export:
            self.export_fps = args.export_fps
            import shutil
            shutil.rmtree(EXPORT_DIR)
            os.mkdir(EXPORT_DIR)
            self.exporter = Exporter(EXPORT_DIR, self.margin, self.margin, self.width, self.height)

    def reset(self):
        self.files = {}
        self.peers = {}
        self._segments_by_id = {}
        self.torrent_length = 0

    def enable_3d(self):
        self._3d_enabled = True

    def run(self):
        window_width = self.width + self.margin*2
        window_height = self.height + self.margin*2
        glutInit(sys.argv)
        glutInitDisplayMode(self.gl_display_mode)
        if self.args.fullscreen:
            glutGameModeString("%dx%d:32@75" % (window_width, window_height))
            glutEnterGameMode()
            glutSetCursor(GLUT_CURSOR_NONE)
        else:
            glutInitWindowSize(window_width, window_height)
            glutInitWindowPosition(
                (glutGet(GLUT_SCREEN_WIDTH) - window_width) / 2,
                (glutGet(GLUT_SCREEN_HEIGHT) - window_height) / 2)
            glutCreateWindow("")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL()
        self.ReSizeGLScene(window_width, window_height)
        glutMainLoop()

    def handle_torrent_message(self, path, args, types, src, data):
        self.num_files, self.download_duration, self.total_size = args

    def handle_file_message(self, path, args, types, src, data):
        (filenum, offset, length) = args
        f = self.files[filenum] = self.file_class(self, filenum, offset, length)
        self.logger.debug("added file %s" % f)
        self.torrent_length += length
        self.added_file(f)
        if len(self.files) == self.num_files:
            self.logger.debug("added all files")
            self.added_all_files()

    def handle_chunk_message(self, path, args, types, src, data):
        self.logger.debug("handling chunk message")
        (chunk_id, torrent_position, byte_size, filenum, peer_id, t) = args
        if filenum in self.files:
            f = self.files[filenum]
            begin = torrent_position - f.offset
            end = begin + byte_size
            chunk = self.chunk_class(
                chunk_id, begin, end, byte_size, filenum, f,
                peer_id, t, self.current_time(), self)
            self.files[filenum].add_chunk(chunk)
        else:
            print "ignoring chunk from undeclared file %s" % filenum

    def handle_segment_message(self, path, args, types, src, data):
        (segment_id, torrent_position, byte_size, filenum,
         peer_id, t, duration) = args
        if filenum in self.files:
            f = self.files[filenum]
            begin = torrent_position - f.offset
            end = begin + byte_size
            segment = self.segment_class(
                segment_id, begin, end, byte_size, filenum, f,
                peer_id, t, duration, self.current_time(), self)
            self._segments_by_id[segment_id] = segment

            self.add_segment(segment)
        else:
            print "ignoring segment from undeclared file %s" % filenum

    def handle_peer_message(self, path, args, types, src, data):
        peer_id, addr, bearing = args
        self.peers[peer_id] = self.peer_class(self, addr, bearing)

    def add_segment(self, segment):
        peer = self.peers[segment.peer_id]
        segment.peer = peer

        f = self.files[segment.filenum]
        segment.f = f
        segment.pan = 0.5
        f.add_segment(segment)

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

    def handle_shutdown(self, path, args, types, src, data):
        self.exiting = True

    def handle_reset(self, *args):
        self.reset()

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
        self.orchestra = OrchestraController(self.orchestra_port)
        self.server = OscReceiver(log_filename=log_filename)
        self.server.add_method("/torrent", "ifi", self.handle_torrent_message)
        self.server.add_method("/file", "iii", self.handle_file_message)
        self.server.add_method("/chunk", "iiiiif", self.handle_chunk_message)
        self.server.add_method("/segment", "iiiiiff", self.handle_segment_message)
        self.server.add_method("/peer", "isf", self.handle_peer_message)
        self.server.add_method("/reset", "", self.handle_reset)
        self.server.add_method("/shutdown", "", self.handle_shutdown)
        self.server.start()
        self.waveform_server = None

    def setup_waveform_server(self):
        self.waveform_server = OscReceiver(proto=liblo.UDP)
        self.waveform_server.add_method("/amp", "if", self.handle_amp_message)
        self.waveform_server.add_method("/waveform", "if", self.handle_waveform_message)
        self.waveform_server.start()

    def InitGL(self):
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClearAccum(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glShadeModel(GL_SMOOTH)
        glutMouseFunc(self._mouse_clicked)
        glutMotionFunc(self._mouse_moved)
        glutSpecialFunc(self._special_key_pressed)

    def ReSizeGLScene(self, window_width, window_height):
        if window_height == 0:
            window_height = 1
        glViewport(0, 0, window_width, window_height)
        self.width = window_width - 2*self.margin
        self.height = window_height - 2*self.margin
        self._aspect_ratio = float(window_width) / window_height
        self._refresh_layers()
        if not self._3d_enabled:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0.0, window_width, window_height, 0.0, -1.0, 1.0)
            glMatrixMode(GL_MODELVIEW)

    def _refresh_layers(self):
        for layer in self._layers:
            layer.refresh()

    def DrawGLScene(self):
        if self.exiting:
            sys.exit()

        try:
            self._draw_gl_scene_error_handled()
        except Exception as error:
            traceback_printer.print_traceback()
            self.exiting = True
            raise error

    def _draw_gl_scene_error_handled(self):
        if self._camera_script:
            self._move_camera_by_script()

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
            glTranslatef(self.margin, self.margin, 0)
            if self.args.border:
                self.draw_border()
            self.handle_incoming_messages()
            if self._3d_enabled and not self._accum_enabled:
                self.set_perspective(
                    0, 0,
                    -self._camera_position.x, -self._camera_position.y, self._camera_position.z)
            self.render()
            if self.show_fps:
                self.update_fps_history()
                self.show_fps_if_timely()

        glutSwapBuffers()
        self.previous_frame_time = self.now
        if self.export:
            if self.export_finished():
                self.exiting = True
            else:
                self.exporter.export_frame()

    def export_finished(self):
        return False

    def handle_incoming_messages(self):
        if not self.args.standalone:
            if self.osc_log:
                self.server.serve_from_log_until(self.now)
            else:
                self.server.serve()
                if self.waveform_server:
                    self.waveform_server.serve()

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
        glDisable(GL_LINE_SMOOTH)
        glLineWidth(1)
        glColor3f(BORDER_OPACITY, BORDER_OPACITY, BORDER_OPACITY)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def keyPressed(self, key, x, y):
        if key == ESCAPE:
            self.synth.stop_all()
            self.exiting = True
        elif key == 's':
            self._dump_screen()

    def _dump_screen(self):
        self._screen_dumper.export_frame()

    def playing_segment(self, segment):
        self.orchestra.visualizing_segment(segment.id)
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
        self.orchestra.set_listener_position(x, y)

    def set_listener_orientation(self, orientation):
        self.orchestra.set_listener_orientation(-orientation)

    def place_segment(self, segment_id, x, y, duration):
        self.orchestra.place_segment(segment_id, -x, y, duration)

    def _mouse_clicked(self, button, state, x, y):
        if button == GLUT_LEFT_BUTTON:
            self._dragging_orientation = (state == GLUT_DOWN)
        else:
            self._dragging_orientation = False
            if button == GLUT_RIGHT_BUTTON:
                self._dragging_y_position = (state == GLUT_DOWN)
        if state == GLUT_DOWN:
            self._drag_x_previous = x
            self._drag_y_previous = y

    def _mouse_moved(self, x, y):
        if self._dragging_orientation:
            self._disable_camera_script()
            self._set_camera_orientation(
                self._camera_y_orientation + x - self._drag_x_previous,
                self._camera_x_orientation - y + self._drag_y_previous)
            self._print_camera_settings()
        elif self._dragging_y_position:
            self._disable_camera_script()
            self._camera_position.y += CAMERA_Y_SPEED * (y - self._drag_y_previous)
            self._print_camera_settings()
        self._drag_x_previous = x
        self._drag_y_previous = y

    def _disable_camera_script(self):
        self._camera_script = None

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
        print "%s, %s, %s" % (
            self._camera_position.v, self._camera_y_orientation, self._camera_x_orientation)

    def _set_camera_position(self, position):
        self._camera_position = position
        if not self._standalone:
            self.set_listener_position(position.z, position.x)

    def _set_camera_orientation(self, y_orientation, x_orientation):
        self._camera_y_orientation = y_orientation
        self._camera_x_orientation = x_orientation
        if not self._standalone:
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
        # dx = -(pixdx*xwsize/self.width + eyedx*self.near/focus)
        # dy = -(pixdy*ywsize/self.height + eyedy*self.near/focus)
        # I don't understand why this modification solved the problem (focus was 1.0)
        dx = -(pixdx*xwsize/self.width)
        dy = -(pixdy*ywsize/self.height)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glFrustum (left + dx, right + dx, bottom + dy, top + dy, self.near, self.far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glRotatef(self._camera_x_orientation, 1.0, 0.0, 0.0)
        glRotatef(self._camera_y_orientation, 0.0, 1.0, 0.0)
        glTranslatef(self._camera_position.x, self._camera_position.y, self._camera_position.z)

    def enable_accum(self):
        self.gl_display_mode |= GLUT_ACCUM
        self._accum_enabled = True

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
        if not self.waveform_server:
            self.setup_waveform_server()
        self.synth.subscribe_to_amp(self.waveform_server.port)

    def subscribe_to_waveform(self):
        if not self.waveform_server:
            self.setup_waveform_server()
        self.synth.subscribe_to_waveform(self.waveform_server.port)

    def _move_camera_by_script(self):
        position, orientation = self._camera_script.position_and_orientation(
            self.current_time())
        self._set_camera_position(position)
        self._set_camera_orientation(orientation.y, orientation.x)

    def new_layer(self, rendering_function):
        layer = Layer(rendering_function, self.new_display_list_id())
        self._layers.append(layer)
        return layer

    def new_display_list_id(self):
        self._display_list_count += 1
        return self._display_list_count

    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument('-port', type=int)
        parser.add_argument('-sync', action='store_true')
        parser.add_argument('-width', dest='width', type=int, default=640)
        parser.add_argument('-height', dest='height', type=int, default=480)
        parser.add_argument('-margin', dest='margin', type=int, default=0)
        parser.add_argument('-show-fps', dest='show_fps', action='store_true')
        parser.add_argument('-osc-log', dest='osc_log')
        parser.add_argument('-export', dest='export', action='store_true')
        parser.add_argument('-export-fps', dest='export_fps', default=30.0, type=float)
        parser.add_argument("-waveform", dest="waveform", action='store_true')
        parser.add_argument("-waveform-gain", dest="waveform_gain", default=1, type=float)
        parser.add_argument("-camera-script", dest="camera_script", type=str)
        parser.add_argument("-border", action="store_true")
        parser.add_argument("-fullscreen", action="store_true")
        parser.add_argument("-standalone", action="store_true")

def run(visualizer_class):
    print "Hit ESC key to quit."

    parser = argparse.ArgumentParser()
    visualizer_class.add_parser_arguments(parser)
    args = parser.parse_args()

    visualizer_class(args).run()
