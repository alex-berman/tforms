from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'

class Chunk:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

class Visualizer:
    def __init__(self):
        self.chunks = []
        self.setup_osc()
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
        glutInitWindowSize(640, 480)
        glutInitWindowPosition(0, 0)
        glutCreateWindow("")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL(640, 480)
        glutMainLoop()

    def handle_chunk(self, path, args, types, src, data):
        (begin, end, duration, pan) = args
        chunk = Chunk(begin, end)
        self.chunks.append(chunk)

    def setup_osc(self):
        self.server = liblo.Server(VISUALIZER_PORT)
        self.server.add_method("/chunk", "ifff", self.handle_chunk)

    def InitGL(self, Width, Height):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClearDepth(1.0)
        glDepthFunc(GL_LESS)
        glEnable(GL_DEPTH_TEST)
        glShadeModel(GL_SMOOTH)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)

        glMatrixMode(GL_MODELVIEW)

    def ReSizeGLScene(self, Width, Height):
        if Height == 0:
                Height = 1

        glViewport(0, 0, Width, Height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def DrawGLScene(self):
        self.server.recv(10)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        if len(self.chunks) > 0:
            self.draw_chunks()

        glutSwapBuffers()


    def draw_chunks(self):
        glTranslatef(1.0, 0.0, -16.0)
        self.y_ratio = 0.0000001
        for chunk in self.chunks:
            self.draw_chunk(chunk)

    def draw_chunk(self, chunk):
        x1 = -1
        x2 = 1
        y1 = self.y_ratio * chunk.begin
        y2 = self.y_ratio * chunk.end
        print y1, y2
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
