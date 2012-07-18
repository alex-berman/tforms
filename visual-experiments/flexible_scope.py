from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
import time
import threading
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'
MIN_DURATION = 0.1

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
        self.position_of_first_active_chunk = 0

    def add_chunk(self, chunk):
        if len(self.chunks) == 0:
            self.min_byte = chunk.begin
            self.max_byte = chunk.end
        else:
            self.min_byte = min(self.min_byte, chunk.begin)
            self.max_byte = max(self.max_byte, chunk.end)
        self.chunks.append(chunk)

    def update_x_scope(self):
        self.now = time.time()
        active_chunk_positions = filter(lambda position: self.chunk_at_position_is_active(position),
                                        range(self.position_of_first_active_chunk,
                                              len(self.chunks)))
        if len(active_chunk_positions) == 0:
            self.position_of_first_active_chunk = len(self.chunks)
            current_min_byte = self.min_byte
            current_max_byte = self.max_byte
        else:
            self.position_of_first_active_chunk = max(active_chunk_positions)
            active_chunks = [self.chunks[position] for position in active_chunk_positions]
            current_min_byte = min(active_chunks, key=lambda chunk: chunk.begin).begin
            current_max_byte = max(active_chunks, key=lambda chunk: chunk.end).end
        self._smoothed_min_byte.smooth(current_min_byte)
        self._smoothed_max_byte.smooth(current_max_byte)
        self.byte_offset = self._smoothed_min_byte.value()
        diff = self._smoothed_max_byte.value() - self._smoothed_min_byte.value()
        if diff == 0:
            self.x_ratio = 1
        else:
            self.x_ratio = 1.0 / diff

    def chunk_at_position_is_active(self, position):
        chunk = self.chunks[position]
        age = self.now - chunk.arrival_time
        return age < chunk.duration

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
            pan_x = (chunk.pan - 0.5)
            y1 = int(y - 3 + 40 * pan_x * actuality)
            y2 = int(y + 3 + 40 * pan_x * actuality)
            x1 = int(f.byte_to_coord(chunk.begin) * self.width)
            x2 = int(f.byte_to_coord(chunk.end) * self.width)
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
