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
MARGIN = 30
BORDER_OPACITY = 0.7

class Chunk:
    def __init__(self, torrent_position, byte_size, filenum, file_offset, pan, duration, arrival_time):
        self.torrent_position = torrent_position
        self.byte_size = byte_size
        self.filenum = filenum
        file_position = torrent_position - file_offset
        self.begin = file_position
        self.end = file_position + byte_size
        self.pan = pan
        self.duration = duration
        self.arrival_time = arrival_time

class Visualizer:
    def __init__(self, args):
        self.sync = args.sync
        self.width = args.width
        self.height = args.height

        self.first_frame = True
        self.synth_controller = SynthController()
        self.setup_osc()

    def run(self):
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

    def handle_chunk_message(self, path, args, types, src, data):
        (chunk_id, torrent_position, byte_size, filenum, file_offset, duration, pan) = args
        chunk = Chunk(torrent_position, byte_size, filenum, file_offset, pan, duration, time.time())
        self.add_chunk(chunk)

    def setup_osc(self):
        self.server = liblo.Server(VISUALIZER_PORT)
        self.server.add_method("/chunk", "iiiiiff", self.handle_chunk_message)
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

        now = time.time()
        if self.first_frame:
            if self.sync:
                self.synth_controller.sync_beep()
            self.first_frame = False
        else:
            self.time_increment = now - self.previous_frame_time
            glTranslatef(MARGIN, MARGIN, 0)
            self.draw_border()
            self.render()

        glutSwapBuffers()
        self.previous_frame_time = now

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


def run(visualizer_class):
    print "Hit ESC key to quit."

    parser = argparse.ArgumentParser()
    parser.add_argument('-sync', action='store_true')
    parser.add_argument('-width', dest='width', type=int, default=640)
    parser.add_argument('-height', dest='height', type=int, default=480)
    args = parser.parse_args()

    visualizer_class(args).run()
