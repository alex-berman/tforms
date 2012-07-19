from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
import time
import threading
import argparse

sys.path.append("..")
from orchestra import VISUALIZER_PORT
from synth_controller import SynthController

ESCAPE = '\033'
MIN_DURATION = 0.1
ARRIVAL_SIZE = 10
MARGIN = 30
BORDER_OPACITY = 0.7
APPEND_MARGIN = 0.15
PREPEND_MARGIN = 0.05

class Smoother:
    RESPONSE_FACTOR = 0.2

    def __init__(self):
        self._current_value = None

    def smooth(self, new_value):
        if self._current_value:
            self._current_value += (new_value - self._current_value) * self.RESPONSE_FACTOR
        else:
            self._current_value = new_value

    def value(self):
        return self._current_value

class Chunk:
    def __init__(self, torrent_position, byte_size, filenum, file_offset, pan, duration, arrival_time):
        self.torrent_position = torrent_position
        self.byte_size = byte_size
        self.filenum = filenum
        file_position = torrent_position - file_offset
        self.begin = file_position
        self.end = file_position + byte_size
        self.pan = pan
        self.duration = max(duration, MIN_DURATION)
        self.arrival_time = arrival_time

class File:
    def __init__(self, filenum):
        self.filenum = filenum
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.min_byte = None
        self.max_byte = None
        self.x_ratio = None
        self.chunks = []

    def add_chunk(self, chunk):
        if len(self.chunks) == 0:
            self.min_byte = chunk.begin
            self.max_byte = chunk.end
        else:
            self.min_byte = min(self.min_byte, chunk.begin)
            self.max_byte = max(self.max_byte, chunk.end)
        self.chunks.append(chunk)

    def update_x_scope(self):
        self._smoothed_min_byte.smooth(self.min_byte)
        self._smoothed_max_byte.smooth(self.max_byte)
        self.byte_offset = self._smoothed_min_byte.value()
        diff = self._smoothed_max_byte.value() - self._smoothed_min_byte.value()
        if diff == 0:
            self.x_ratio = 1
        else:
            self.x_ratio = 1.0 / diff

    def byte_to_coord(self, byte):
        return self.x_ratio * (byte - self.byte_offset)

class Visualizer:
    def __init__(self, args):
        self.sync = args.sync
        self.width = args.width
        self.height = args.height

        self.safe_width = int(self.width * (1 - APPEND_MARGIN - PREPEND_MARGIN))
        self.prepend_margin_width = int(self.width * PREPEND_MARGIN)
        self.files = {}
        self.chunks = []
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()
        self.first_frame = True
        self.synth_controller = SynthController()
        self.setup_osc()

        window_width = self.width + MARGIN*2
        window_height = self.height + MARGIN*2
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
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

    def handle_chunk(self, path, args, types, src, data):
        (chunk_id, torrent_position, byte_size, filenum, file_offset, duration, pan) = args
        chunk = Chunk(torrent_position, byte_size, filenum, file_offset, pan, duration, time.time())
        if not filenum in self.files:
            self.files[filenum] = File(filenum)
        self.files[filenum].add_chunk(chunk)
        self.chunks.append(chunk)

    def setup_osc(self):
        self.server = liblo.Server(VISUALIZER_PORT)
        self.server.add_method("/chunk", "iiiiiff", self.handle_chunk)
        server_thread = threading.Thread(target=self.serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def serve_osc(self):
        while True:
            self.server.recv()

    def InitGL(self):
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

    def ReSizeGLScene(self, _width, _height):
        if _height == 0:
            _height = 1
        glViewport(0, 0, _width, _height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, _width, _height, 0.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW)

    def DrawGLScene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if self.sync:
            if self.first_frame:
                self.synth_controller.sync_beep()
                self.first_frame = False

        glTranslatef(MARGIN, MARGIN, 0)
        self.draw_border()
        if len(self.chunks) > 0:
            self.draw_chunks()

        glutSwapBuffers()


    def draw_chunks(self):
        self.update_y_scope()
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        f.update_x_scope()
        for chunk in f.chunks:
            age = time.time() - chunk.arrival_time
            if age > chunk.duration:
                actuality = 0
            else:
                actuality = 1 - float(age) / chunk.duration
            y_offset = actuality * 10
            height = 3 + actuality * 10
            y1 = int(y + y_offset)
            y2 = int(y + y_offset + height)
            x1 = self.prepend_margin_width + int(f.byte_to_coord(chunk.begin) * self.safe_width)
            x2 = self.prepend_margin_width + int(f.byte_to_coord(chunk.end) * self.safe_width)
            x1, x2 = self.upscale(x1, x2, actuality)
            if x2 == x1:
                x2 = x1 + 1
            opacity = 0.2 + (actuality * 0.8)
            glColor3f(1-opacity, 1-opacity, 1-opacity)
            glBegin(GL_LINE_LOOP)
            glVertex2i(x1, y2)
            glVertex2i(x2, y2)
            glVertex2i(x2, y1)
            glVertex2i(x1, y1)
            glEnd()

    def upscale(self, x1, x2, actuality):
        unscaled_size = x2 - x1
        desired_size = actuality * ARRIVAL_SIZE
        if desired_size > unscaled_size:
            mid = (x1 + x2) / 2
            half_desired_size = int(desired_size/2)
            x1 = mid - half_desired_size
            x2 = mid + half_desired_size
        return (x1, x2)

    def filenum_to_y_coord(self, filenum):
        return self.y_ratio * (filenum - self.filenum_offset + 1)

    def update_y_scope(self):
        min_filenum = min(self.chunks, key=lambda chunk: chunk.filenum).filenum
        max_filenum = max(self.chunks, key=lambda chunk: chunk.filenum).filenum
        self._smoothed_min_filenum.smooth(float(min_filenum))
        self._smoothed_max_filenum.smooth(float(max_filenum))
        self.filenum_offset = self._smoothed_min_filenum.value()
        diff = self._smoothed_max_filenum.value() - self._smoothed_min_filenum.value() + 1
        self.y_ratio = float(self.height) / (diff + 1)

    def draw_border(self):
        x1 = y1 = -1
        x2 = self.width
        y2 = self.height
        glColor3f(BORDER_OPACITY, BORDER_OPACITY, BORDER_OPACITY)
        glBegin(GL_LINE_LOOP)
        glVertex2i(x1, y2)
        glVertex2i(x2, y2)
        glVertex2i(x2, y1)
        glVertex2i(x1, y1)
        glEnd()

    def keyPressed(self, *args):
        if args[0] == ESCAPE:
                sys.exit()


print "Hit ESC key to quit."

parser = argparse.ArgumentParser()
parser.add_argument('-sync', action='store_true')
parser.add_argument('-width', dest='width', type=int, default=640)
parser.add_argument('-height', dest='height', type=int, default=480)
args = parser.parse_args()
Visualizer(args)
