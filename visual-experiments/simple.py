from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
import time
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'
HIGHLIGHT_TIME = 3

class Chunk:
    def __init__(self, begin, end, arrival_time):
        self.begin = begin
        self.end = end
        self.arrival_time = arrival_time

class Visualizer:
    def __init__(self, width=640, height=480):
        self.chunks = []
        self.y_ratio = None
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
        (begin, end, duration, pan) = args
        chunk = Chunk(begin, end, time.time())
        self.chunks.append(chunk)

    def setup_osc(self):
        self.server = liblo.Server(VISUALIZER_PORT)
        self.server.add_method("/chunk", "ifff", self.handle_chunk)

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
        min_byte = min(self.chunks, key=lambda chunk: chunk.begin).begin
        max_byte = max(self.chunks, key=lambda chunk: chunk.end).end
        target_y_ratio = float(self.height) / max_byte
        if self.y_ratio:
            self.y_ratio += (target_y_ratio - self.y_ratio) * 0.1
        else:
            self.y_ratio = target_y_ratio

        for chunk in self.chunks:
            self.draw_chunk(chunk)

    def draw_chunk(self, chunk):
        x1 = 100
        x2 = 110
        y1 = self.y_ratio * chunk.begin
        y2 = self.y_ratio * chunk.end
        age = time.time() - chunk.arrival_time
        if age > HIGHLIGHT_TIME:
            actuality = 0
        else:
            actuality = float(age) / HIGHLIGHT_TIME
        opacity = 0.5 + actuality / 2
        glColor3f(opacity, opacity, opacity)
        glBegin(GL_QUADS)
        glVertex3f(x1, y2, 0.0)
        glVertex3f(x2, y2, 0.0)
        glVertex3f(x2, y1, 0.0)
        glVertex3f(x1, y1, 0.0)
        glEnd()

    def keyPressed(self, *args):
        if args[0] == ESCAPE:
                sys.exit()

print "Hit ESC key to quit."
Visualizer()
