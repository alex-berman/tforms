from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
import time
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'
HIGHLIGHT_TIME = 0.3

class Smoother:
    RESPONSE_FACTOR = 0.1

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
    def __init__(self, torrent_position, byte_size, filenum, file_offset, pan, arrival_time):
        self.torrent_position = torrent_position
        self.byte_size = byte_size
        self.filenum = filenum
        file_position = torrent_position - file_offset
        self.begin = file_position
        self.end = file_position + byte_size
        self.pan = pan
        self.arrival_time = arrival_time

class File:
    def __init__(self, filenum):
        self.filenum = filenum
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.x_ratio = None
        self.chunks = []

    def add_chunk(self, chunk):
        self.chunks.append(chunk)
        self.update_x_scope()

    def update_x_scope(self):
        min_byte = min(self.chunks, key=lambda chunk: chunk.begin).begin
        max_byte = max(self.chunks, key=lambda chunk: chunk.end).end
        self._smoothed_min_byte.smooth(min_byte)
        self._smoothed_max_byte.smooth(max_byte)
        self.byte_offset = self._smoothed_min_byte.value()
        diff = self._smoothed_max_byte.value() - self._smoothed_min_byte.value()
        if diff == 0:
            self.x_ratio = 1
        else:
            self.x_ratio = 1.0 / diff

    def byte_to_coord(self, byte):
        return self.x_ratio * (byte - self.byte_offset)

class Visualizer:
    def __init__(self, width=640, height=480):
        self.files = {}
        self.chunks = []
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()

        self.setup_osc()
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
        glutInitWindowSize(width, height)
        glutInitWindowPosition(0, 0)
        glutCreateWindow("")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL()
        self.ReSizeGLScene(width, height)
        glutMainLoop()

    def handle_chunk(self, path, args, types, src, data):
        (torrent_position, byte_size, filenum, file_offset, duration, pan) = args
        chunk = Chunk(torrent_position, byte_size, filenum, file_offset, pan, time.time())
        if not filenum in self.files:
            self.files[filenum] = File(filenum)
        self.files[filenum].add_chunk(chunk)
        self.chunks.append(chunk)

    def setup_osc(self):
        self.server = liblo.Server(VISUALIZER_PORT)
        self.server.add_method("/chunk", "iiiiff", self.handle_chunk)

    def InitGL(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

    def ReSizeGLScene(self, _width, _height):
        if _height == 0:
                _height = 1
        self.width = _width
        self.height = _height

        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, self.width, self.height, 0.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW)

    def DrawGLScene(self):
        self.server.recv(10)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if len(self.chunks) > 0:
            self.draw_chunks()

        glutSwapBuffers()


    def draw_chunks(self):
        self.update_y_scope()
        for f in self.files.values():
            self.draw_file(f)

    def draw_file(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        for chunk in f.chunks:
            age = time.time() - chunk.arrival_time
            if age > HIGHLIGHT_TIME:
                actuality = 0
            else:
                actuality = 1 - float(age) / HIGHLIGHT_TIME
            pan_x = (chunk.pan - 0.5)
            y1 = int(y - 3 + 40 * pan_x * actuality)
            y2 = int(y + 3 + 40 * pan_x * actuality)
            x1 = int(f.byte_to_coord(chunk.begin) * self.width)
            x2 = int(f.byte_to_coord(chunk.end) * self.width)
            if x2 == x1:
                x2 = x1 + 1
            opacity = 0.2 + (actuality * 0.8)
            glColor3f(opacity, opacity, opacity)
            glBegin(GL_LINE_STRIP)
            glVertex2i(x1, y2)
            glVertex2i(x2, y2)
            glVertex2i(x2, y1)
            glVertex2i(x1, y1)
            glEnd()

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

    def keyPressed(self, *args):
        if args[0] == ESCAPE:
                sys.exit()

print "Hit ESC key to quit."
Visualizer()
