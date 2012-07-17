from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
import time
import threading
import collections
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'
MIN_DURATION = 0.1
COMPLETION_OPACITY = 0.5

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
    def __init__(self, chunk_id, torrent_position, byte_size, filenum, file_offset, pan, duration, arrival_time):
        self.id = chunk_id
        self.torrent_position = torrent_position
        self.byte_size = byte_size
        self.filenum = filenum
        file_position = torrent_position - file_offset
        self.begin = file_position
        self.end = file_position + byte_size
        self.pan = pan
        self.duration = max(duration, MIN_DURATION)
        self.arrival_time = arrival_time

class Completion:
    def __init__(self, chunk):
        self.begin = chunk.begin
        self.end = chunk.end

    def append(self, chunk):
        self.end = chunk.end

class File:
    def __init__(self, filenum):
        self.filenum = filenum
        self._smoothed_min_byte = Smoother()
        self._smoothed_max_byte = Smoother()
        self.min_byte = None
        self.max_byte = None
        self.x_ratio = None
        self.chunks = collections.OrderedDict()
        self.completions = []

    def add_chunk(self, chunk):
        if len(self.chunks) == 0:
            self.min_byte = chunk.begin
            self.max_byte = chunk.end
        else:
            self.min_byte = min(self.min_byte, chunk.begin)
            self.max_byte = max(self.max_byte, chunk.end)
        self.chunks[chunk.id] = chunk

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

    def complete_chunk(self, chunk):
        appendable_completion = self.get_appendable_completion(chunk)
        if appendable_completion:
            appendable_completion.append(chunk)
            del self.chunks[chunk.id]
        else:
            self.add_completion(chunk)

    def get_appendable_completion(self, chunk):
        for completion in self.completions:
            if completion.end == chunk.begin:
                return completion

    def add_completion(self, chunk):
        self.completions.append(Completion(chunk))

class Visualizer:
    def __init__(self, width=640, height=480):
        self.files = {}
        self._smoothed_min_filenum = Smoother()
        self._smoothed_max_filenum = Smoother()
        self.lock = threading.Lock()

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
        (chunk_id, torrent_position, byte_size, filenum, file_offset, duration, pan) = args
        chunk = Chunk(chunk_id, torrent_position, byte_size, filenum, file_offset, pan, duration, time.time())
        with self.lock:
            if not filenum in self.files:
                self.add_file(filenum)
            self.files[filenum].add_chunk(chunk)

    def add_file(self, filenum):
        if len(self.files) == 0:
            self.min_filenum = self.max_filenum = filenum
        else:
            self.min_filenum = min(self.min_filenum, filenum)
            self.max_filenum = max(self.max_filenum, filenum)
        self.files[filenum] = File(filenum)

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
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        with self.lock:
            print sum([len(f.chunks) for f in self.files.values()])
            if len(self.files) > 0:
                self.update_y_scope()
                for f in self.files.values():
                    self.draw_file(f)
        glutSwapBuffers()

    def draw_file(self, f):
        f.update_x_scope()
        self.draw_completions(f)
        self.draw_chunks(f)

    def draw_completions(self, f):
        opacity = COMPLETION_OPACITY
        glColor3f(opacity, opacity, opacity)
        y = int(self.filenum_to_y_coord(f.filenum))
        for completion in f.completions:
            x1 = int(f.byte_to_coord(completion.begin) * self.width)
            x2 = int(f.byte_to_coord(completion.end) * self.width)
            glBegin(GL_LINES)
            glVertex2i(x1, y)
            glVertex2i(x2, y)
            glEnd()

    def draw_chunks(self, f):
        y = self.filenum_to_y_coord(f.filenum)
        for chunk in f.chunks.values():
            age = time.time() - chunk.arrival_time
            if age > chunk.duration:
                f.complete_chunk(chunk)
            else:
                actuality = 1 - float(age) / chunk.duration
                pan_x = (chunk.pan - 0.5)
                y1 = int(y - 3 + 40 * pan_x * actuality)
                y2 = int(y + 3 + 40 * pan_x * actuality)
                x1 = int(f.byte_to_coord(chunk.begin) * self.width)
                x2 = int(f.byte_to_coord(chunk.end) * self.width)
                if x2 == x1:
                    x2 = x1 + 1
                opacity = COMPLETION_OPACITY + actuality * (1 - COMPLETION_OPACITY)
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
        self._smoothed_min_filenum.smooth(float(self.min_filenum))
        self._smoothed_max_filenum.smooth(float(self.max_filenum))
        self.filenum_offset = self._smoothed_min_filenum.value()
        diff = self._smoothed_max_filenum.value() - self._smoothed_min_filenum.value() + 1
        self.y_ratio = float(self.height) / (diff + 1)

    def keyPressed(self, *args):
        if args[0] == ESCAPE:
                sys.exit()

print "Hit ESC key to quit."
Visualizer()
