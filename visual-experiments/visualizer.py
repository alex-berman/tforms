import sys
import OpenGL
OpenGL.ERROR_LOGGING = "-check-opengl-errors" in sys.argv
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

import argparse
import os
import collections
import logging
import math
import subprocess
import platform
import time
from exporter import Exporter

dirname = os.path.dirname(__file__)
if dirname:
    sys.path.append(dirname + "/..")
else:
    sys.path.append("..")
from orchestra_controller import OrchestraController
import osc
import simple_osc_receiver
from stopwatch import Stopwatch
import traceback_printer
from camera_script_interpreter import CameraScriptInterpreter
from message_log import *
text_renderer_module = __import__("text_renderer")

logging.basicConfig(filename="visualizer.log", 
                    level=logging.DEBUG, 
                    filemode="w")

ESCAPE = '\033'
BORDER_OPACITY = 0.7
FAKE_CHUNK_DURATION = 0.1

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

TEXT_RENDERERS = {
    "glut": "GlutTextRenderer",
    "ftgl": "FtglTextRenderer"
}

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
                 filenum, f, peer, t,
                 arrival_time, visualizer):
        self.id = chunk_id
        self.begin = begin
        self.end = end
        self.byte_size = byte_size
        self.filenum = filenum
        self.f = f
        self.peer = peer
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
                 filenum, f, peer, t, duration,
                 arrival_time, visualizer):
        Chunk.__init__(self, chunk_id, begin, end, byte_size,
                 filenum, f, peer, t,
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
    def __init__(self, visualizer, addr, bearing, pan, location):
        self.visualizer = visualizer
        self.addr = addr
        self.bearing = bearing
        self.pan = pan
        if location == "":
            self.location = None
            self.place_name = None
        else:
            x, y, self.place_name = location.split(",")
            self.place_name = self.place_name.decode("unicode_escape")
            self.location = map(float, (x, y))

    def add_segment(self, segment):
        pass


class Layer:
    def __init__(self, rendering_function, display_list_id):
        self._rendering_function = rendering_function
        self._updated = False
        self._display_list_id = display_list_id

    def draw(self):
        if not self._updated:
            glNewList(self._display_list_id, GL_COMPILE)
            self._rendering_function()
            glEndList()
            self._updated = True
        glCallList(self._display_list_id)

    def refresh(self):
        self._updated = False


class Visualizer:
    def __init__(self, args,
                 file_class=File,
                 chunk_class=Chunk,
                 segment_class=Segment,
                 peer_class=Peer):
        if hasattr(self, "_initialized") and self._initialized:
            return
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
        self.capture_message_log = args.capture_message_log
        self.play_message_log = args.play_message_log
        self.waveform_gain = args.waveform_gain
        self._standalone = args.standalone
        self._target_aspect_ratio = self._get_aspect_ratio_from_args()

        self.logger = logging.getLogger("visualizer")
        self.reset()
        self._frame_count = 0
        self.exiting = False
        self.time_increment = 0
        self.stopwatch = Stopwatch()
        self._synth_instance = None
        self._synth_port = None
        self._synced = False
        self._layers = []
        self._warned_about_missing_pan_segment = False
        self.gl_display_mode = GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH
        self._accum_enabled = False
        self._3d_enabled = False
        self.fovy = 45
        self.near = 0.1
        self.far = 100.0
        self._fullscreen = False
        self._text_renderer_class = getattr(text_renderer_module, TEXT_RENDERERS[args.text_renderer])

        if args.camera_script:
            self._camera_script = CameraScriptInterpreter(args.camera_script)
        else:
            self._camera_script = None

        if self.show_fps:
            self.fps_history = collections.deque(maxlen=10)
            self.previous_shown_fps_time = None

        if not args.standalone:
            if args.port:
                port = args.port
            else:
                port = self._get_orchestra_port()
            self.orchestra_host = args.host
            self.orchestra_port = port
            self.setup_osc()
            self.orchestra.register(self.server.port)

        self._screen_dumper = Exporter(".", self.margin, self.margin, self.width, self.height)
        if self.export:
            self.export_fps = args.export_fps
            import shutil
            if args.export_dir:
                export_dir = args.export_dir
            elif hasattr(args, "sessiondir"):
                export_dir = "%s/rendered_%s" % (args.sessiondir, self.__class__.__name__)
            else:
                export_dir = "export"
            if os.path.exists(export_dir):
                shutil.rmtree(export_dir)
            os.mkdir(export_dir)
            self.exporter = Exporter(export_dir, self.margin, self.margin, self.width, self.height)

        if self.play_message_log:
            self._message_log_reader = MessageLogReader(self.play_message_log)
        if self.capture_message_log:
            self._message_log_writer = MessageLogWriter(self.capture_message_log)
            self._audio_capture_start_time = None

        self._initialized = True

    def _get_aspect_ratio_from_args(self):
        w, h = map(float, self.args.aspect.split(":"))
        return w / h

    def _get_orchestra_port(self):
        if self.args.host == "localhost":
            return self._read_port_from_disk()
        else:
            return self._read_port_from_network_share()

    def _read_port_from_disk(self):
        self._read_port_from_file("server_port.txt")

    def _read_port_from_file(self, filename):
        f = open(filename, "r")
        line = f.read()
        port = int(line)
        f.close()
        return port

    def _read_port_from_network_share(self):
        if platform.system() == "Linux":
            return self._read_port_with_unix_smbclient()
        elif platform.system() == "Windows":
            return self._read_port_via_windows_samba_access()
        else:
            raise Exception("don't know how to handle your OS (%s)" % platform.system())

    def _read_port_with_unix_smbclient(self):
        subprocess.call(
            'smbclient -N \\\\\\\\%s\\\\TorrentialForms -c "get server_port.txt server_remote_port.txt"' % self.args.host,
            shell=True)
        return self._read_port_from_file("server_remote_port.txt")

    def _read_port_via_windows_samba_access(self):
        return self._read_port_from_file(
            '\\\\%s\\TorrentialForms\\server_port.txt' % self.args.host)

    def reset(self):
        self.files = {}
        self.peers = {}
        self.peers_by_addr = {}
        self._segments_by_id = {}
        self.torrent_length = 0
        self.torrent_title = ""
        self.torrent_download_completion_time = None
        self.num_segments = 0
        self.num_received_segments = 0
        self._notified_finished = False

    def enable_3d(self):
        self._3d_enabled = True

    def run(self):
        self.window_width = self.width + self.margin*2
        self.window_height = self.height + self.margin*2

        glutInit(sys.argv)

        if self.args.left is None:
            self._left = (glutGet(GLUT_SCREEN_WIDTH) - self.window_width) / 2
        else:
            self._left = self.args.left

        if self.args.top is None:
            self._top = (glutGet(GLUT_SCREEN_HEIGHT) - self.window_height) / 2
        else:
            self._top = self.args.top

        glutInitDisplayMode(self.gl_display_mode)
        glutInitWindowSize(self.window_width, self.window_height)
        self._non_fullscreen_window = glutCreateWindow("")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL()
        glutPositionWindow(self._left, self._top)

        if self.args.fullscreen:
            self._open_fullscreen_window()
            self._fullscreen = True

        self.ReSizeGLScene(self.window_width, self.window_height)
        glutMainLoop()

    def _open_fullscreen_window(self):
        glutGameModeString("%dx%d:32@75" % (self.window_width, self.window_height))
        glutEnterGameMode()
        glutSetCursor(GLUT_CURSOR_NONE)
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL()
        glutPositionWindow(self._left, self._top)

    def handle_torrent_message(self, num_files, download_duration, total_size,
                               num_chunks, num_segments, encoded_torrent_title):
        self.num_files = num_files
        self.download_duration = download_duration
        self.total_size = total_size
        self.num_segments = num_segments
        self.torrent_title = encoded_torrent_title.decode("unicode_escape")

    def handle_file_message(self, filenum, offset, length):
        f = self.files[filenum] = self.file_class(self, filenum, offset, length)
        self.logger.debug("added file %s" % f)
        self.torrent_length += length
        self.added_file(f)
        if len(self.files) == self.num_files:
            self.logger.debug("added all files")
            self.added_all_files()

    def handle_chunk_message(self, chunk_id, torrent_position, byte_size, filenum, peer_id, t):
        if filenum in self.files:
            f = self.files[filenum]
            peer = self.peers[peer_id]
            begin = torrent_position - f.offset
            end = begin + byte_size
            chunk = self.chunk_class(
                chunk_id, begin, end, byte_size, filenum, f,
                peer, t, self.current_time(), self)
            self.files[filenum].add_chunk(chunk)
        else:
            print "ignoring chunk from undeclared file %s" % filenum

    def handle_segment_message(self, segment_id, torrent_position, byte_size, filenum,
                               peer_id, t, duration):
        if filenum in self.files:
            f = self.files[filenum]
            peer = self.peers[peer_id]
            begin = torrent_position - f.offset
            end = begin + byte_size
            segment = self.segment_class(
                segment_id, begin, end, byte_size, filenum, f,
                peer, t, duration, self.current_time(), self)
            self._segments_by_id[segment_id] = segment

            self.add_segment(segment)
        else:
            print "ignoring segment from undeclared file %s" % filenum

    def handle_peer_message(self, peer_id, addr, bearing, pan, location):
        peer = self.peer_class(self, addr, bearing, pan, location)
        self.peers[peer_id] = peer
        self.peers_by_addr[addr] = peer

    def add_segment(self, segment):
        f = self.files[segment.filenum]
        segment.f = f
        segment.pan = 0.5
        f.add_segment(segment)

        self.pan_segment(segment)
        segment.peer.add_segment(segment)
        self.num_received_segments += 1

    def added_file(self, f):
        pass

    def added_all_files(self):
        pass

    def pan_segment(self, segment):
        if not self._warned_about_missing_pan_segment:
            print "WARNING: pan_segment undefined in visualizer. Orchestra and synth now control panning."
            self._warned_about_missing_pan_segment = True

    def handle_shutdown(self):
        self.exiting = True

    def handle_reset(self):
        self.reset()

    def handle_amp_message(self, segment_id, amp):
        try:
            segment = self._segments_by_id[segment_id]
        except KeyError:
            print "WARNING: amp message for unknown segment ID %s" % segment_id
            return
        self.handle_segment_amplitude(segment, amp)

    def handle_segment_amplitude(self, segment, amp):
        pass

    def handle_waveform_message(self, segment_id, value):
        try:
            segment = self._segments_by_id[segment_id]
        except KeyError:
            print "WARNING: waveform message for unknown segment ID %s" % segment_id
            return
        self.handle_segment_waveform_value(segment, value * self.waveform_gain)

    def handle_segment_waveform_value(self, segment, value):
        pass

    def handle_synth_address(self, port):
        self._synth_instance = None
        self._synth_port = port
        self.synth_address_received()

    def handle_audio_captured_started(self, start_time):
        self._audio_capture_start_time = float(start_time)

    def synth_address_received(self):
        pass

    def setup_osc(self):
        self.orchestra = OrchestraController(self.orchestra_host, self.orchestra_port)
        self.server = simple_osc_receiver.OscReceiver(
            listen=self.args.listen, name="Visualizer")
        self.server.add_method("/torrent", "ifiiis", self._handle_osc_message,
                               "handle_torrent_message")
        self.server.add_method("/file", "iii", self._handle_osc_message,
                               "handle_file_message")
        self.server.add_method("/chunk", "iiiiif", self._handle_osc_message,
                               "handle_chunk_message")
        self.server.add_method("/segment", "iiiiiff", self._handle_osc_message,
                               "handle_segment_message")
        self.server.add_method("/peer", "isffs", self._handle_osc_message,
                               "handle_peer_message")
        self.server.add_method("/reset", "", self._handle_osc_message,
                               "handle_reset")
        self.server.add_method("/shutdown", "", self._handle_osc_message,
                               "handle_shutdown")
        self.server.add_method("/synth_address", "i", self._handle_osc_message,
                               "handle_synth_address")
        self.server.add_method("/audio_captured_started", "s", self._handle_osc_message,
                               "handle_audio_captured_started")
        self.server.start()
        self.waveform_server = None

    def setup_waveform_server(self):
        if not self._standalone:
            import osc_receiver
            self.waveform_server = osc_receiver.OscReceiver(proto=osc.UDP)
            self.waveform_server.add_method("/amp", "if", self._handle_osc_message,
                                            "handle_amp_message")
            self.waveform_server.add_method("/waveform", "if", self._handle_osc_message,
                                            "handle_waveform_message")
            self.waveform_server.start()

    def _handle_osc_message(self, path, args, types, src, handler_name):
        if self.capture_message_log:
            received_time = time.time()
        self._call_handler(handler_name, args)
        if self.capture_message_log:
            if self._audio_capture_start_time is None:
                capture_time = 0.0
                print "WARNING: received OSC before audio capture started: %s" % path
            else:
                capture_time = received_time - self._audio_capture_start_time
            self._message_log_writer.write(
                capture_time, handler_name, args)

    def _call_handler(self, handler_name, args):
        handler = getattr(self, handler_name)
        handler(*args)

    def InitGL(self):
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClearAccum(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glShadeModel(GL_SMOOTH)
        glutMouseFunc(self._mouse_clicked)
        glutMotionFunc(self._mouse_moved)
        glutSpecialFunc(self._special_key_pressed)

    def ReSizeGLScene(self, window_width, window_height):
        self.window_width = window_width
        self.window_height = window_height
        if window_height == 0:
            window_height = 1
        glViewport(0, 0, window_width, window_height)
        self.width = window_width - 2*self.margin
        self.height = window_height - 2*self.margin
        self._aspect_ratio = float(window_width) / window_height
        self.min_dimension = min(self.width, self.height)
        self._refresh_layers()
        if not self._3d_enabled:
            self.configure_2d_projection()
        self.resized_window()

    def resized_window(self):
        pass

    def configure_2d_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.window_width, self.window_height, 0.0, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)

    def _refresh_layers(self):
        for layer in self._layers:
            layer.refresh()

    def DrawGLScene(self):
        if self.exiting:
            self.logger.debug("total number of rendered frames: %s" % self._frame_count)
            if self.stopwatch.get_elapsed_time() > 0:
                self.logger.debug("total FPS: %s" % (float(self._frame_count) / self.stopwatch.get_elapsed_time()))
            if self.args.profile:
                import yappi
                yappi.print_stats(sys.stdout, yappi.SORTTYPE_TTOT)
            glutDestroyWindow(glutGetWindow())
            return

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
            self.current_export_time = float(self._frame_count) / self.export_fps

        self.now = self.current_time()
        is_waiting_for_synth = (self.sync and not self._synth() and not self._synced)
        is_waiting_for_audio_capture_to_start = (
            self.capture_message_log and self._audio_capture_start_time is None)
        if self._frame_count == 0 and \
                not is_waiting_for_synth and \
                not is_waiting_for_audio_capture_to_start:
            self.stopwatch.start()
            if self.sync:
                self._synced = True
        else:
            if self._frame_count == 0:
                self.time_increment = 0
            else:
                self.time_increment = self.now - self.previous_frame_time
            self.handle_incoming_messages()
            self.update()
            if not self.capture_message_log:
                glTranslatef(self.margin, self.margin, 0)
                if self.args.border:
                    self.draw_border()
                if self._3d_enabled and not self._accum_enabled:
                    self.set_perspective(
                        0, 0,
                        -self._camera_position.x, -self._camera_position.y, self._camera_position.z)
                self.render()
                if self.show_fps and self._frame_count > 0:
                    self.update_fps_history()
                    self.show_fps_if_timely()

        if self.export:
            self.exporter.export_frame()
        glutSwapBuffers()
        self.previous_frame_time = self.now
        finished = self.finished()
        if (self.export or self.args.exit_when_finished) and finished:
            self.exiting = True

        if not self._standalone:
            if finished and not self._notified_finished:
                self.orchestra.notify_finished()
                self._notified_finished = True

        if not is_waiting_for_synth:
            self._frame_count += 1

    def finished(self):
        return False

    def handle_incoming_messages(self):
        if self.args.standalone:
            if self.play_message_log:
                self._process_message_log_until(self.now)
        else:
            self.server.serve()
            if self.waveform_server:
                self.waveform_server.serve()

    def _process_message_log_until(self, t):
        messages = self._message_log_reader.read_until(t)
        for _t, handler_name, args in messages:
            self._call_handler(handler_name, args)

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
            # stop_all disabled as it also deletes ~reverb
            # self._synth().stop_all()
            self.exiting = True
        elif key == 's':
            self._dump_screen()
        elif key == 'f':
            if self._fullscreen:
                glutSetCursor(GLUT_CURSOR_INHERIT)
                glutLeaveGameMode()
                glutSetWindow(self._non_fullscreen_window)
                self._fullscreen = False
            else:
                self._open_fullscreen_window()
                self._fullscreen = True

    def _dump_screen(self):
        self._screen_dumper.export_frame()

    def playing_segment(self, segment):
        if not self._standalone:
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
        if self._3d_enabled:
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
        if self._3d_enabled:
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
        if self._3d_enabled:
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
        self._synth().subscribe_to_amp(self.waveform_server.port)

    def subscribe_to_waveform(self):
        if not self._standalone:
            if not self.waveform_server:
                self.setup_waveform_server()
            self._synth().subscribe_to_waveform(self.waveform_server.port)

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
        return glGenLists(1)
    
    def _synth(self):
        if self._synth_instance is None and self._synth_port:
            from synth_controller import SynthController
            self._synth_instance = SynthController(self.logger)
            self._synth_instance.connect(self._synth_port)
        return self._synth_instance

    def draw_text(self, text, size, x, y, font=None, spacing=None,
                  v_align="left", h_align="top"):
        if font is None:
            font = self.args.font
        self.text_renderer(text, size, font).render(x, y, v_align, h_align)

    def text_renderer(self, text, size, font=None):
        if font is None:
            font = self.args.font
        return self._text_renderer_class(self, text, size, font, aspect_ratio=self._target_aspect_ratio)

    def download_completed(self):
        if self.torrent_download_completion_time:
            return True
        else:
            if self.num_segments > 0 and self.num_received_segments == self.num_segments and not self.active():
                self.torrent_download_completion_time = self.current_time()
                return True

    def active(self):
        return False

    def update(self):
        pass

    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("-host", type=str, default="localhost")
        parser.add_argument('-port', type=int)
        parser.add_argument("-listen", type=str)
        parser.add_argument('-sync', action='store_true')
        try:
            parser.add_argument('-width', dest='width', type=int, default=1024)
            parser.add_argument('-height', dest='height', type=int, default=768)
        except argparse.ArgumentError:
            pass
        parser.add_argument("-left", type=int)
        parser.add_argument("-top", type=int)
        parser.add_argument('-margin', dest='margin', type=int, default=0)
        parser.add_argument('-show-fps', dest='show_fps', action='store_true')
        parser.add_argument('-capture-message-log', dest='capture_message_log')
        parser.add_argument('-play-message-log', dest='play_message_log')
        parser.add_argument('-export', dest='export', action='store_true')
        parser.add_argument('-export-fps', dest='export_fps', default=25.0, type=float)
        parser.add_argument('-export-dir')
        parser.add_argument("-waveform", dest="waveform", action='store_true')
        parser.add_argument("-waveform-gain", dest="waveform_gain", default=1, type=float)
        parser.add_argument("-camera-script", dest="camera_script", type=str)
        parser.add_argument("-border", action="store_true")
        parser.add_argument("-fullscreen", action="store_true")
        parser.add_argument("-standalone", action="store_true")
        parser.add_argument("-profile", action="store_true")
        parser.add_argument("-check-opengl-errors", action="store_true")
        parser.add_argument("-exit-when-finished", action="store_true")
        parser.add_argument("--text-renderer", choices=TEXT_RENDERERS.keys(), default="glut")
        parser.add_argument("--font", type=str)
        parser.add_argument("-aspect", type=str, default="1:1",
                            help="Target aspect ratio (e.g. 16:9)")

    @staticmethod
    def add_margin_argument(parser, name):
        parser.add_argument(name, type=str, default="0,0,0,0",
                            help="top,right,bottom,left in relative units")

    def parse_margin_argument(self, argument_string):
        return MarginAttributes.from_argument(argument_string, self)

class MarginAttributes:
    @staticmethod
    def from_argument(argument_string, visualizer):
        fields = ["top", "right", "bottom", "left"]
        margin_attributes = MarginAttributes()
        margin_attributes.visualizer = visualizer
        for field, value_string in zip(fields, argument_string.split(",")):
            setattr(margin_attributes, "relative_%s" % field, float(value_string))
        margin_attributes.update()
        return margin_attributes

    def update(self):
        self.left = int(self.relative_left * self.visualizer.width)
        self.right = int(self.relative_right * self.visualizer.width)
        self.top = int(self.relative_top * self.visualizer.height)
        self.bottom = int(self.relative_bottom * self.visualizer.height)

def run(visualizer_class):
    print "Hit ESC key to quit."

    parser = argparse.ArgumentParser()
    visualizer_class.add_parser_arguments(parser)
    args = parser.parse_args()

    if args.profile:
        import yappi
        yappi.start()

    visualizer_class(args).run()
