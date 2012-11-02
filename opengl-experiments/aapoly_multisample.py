from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys

window_width = 300
window_height = 300
ESCAPE = '\033'

def DrawGLScene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    glEnable(GL_MULTISAMPLE)
    #glHint(GL_MULTISAMPLE_FILTER_HINT_NV, GL_NICEST)

    glColor3f(0,0,0)
    glBegin(GL_POLYGON)
    glVertex2d(10, 10)
    glVertex2d(100, 15)
    glVertex2d(100, 200)
    glVertex2d(10, 100)
    glEnd()

    glutSwapBuffers()

def ReSizeGLScene(_width, _height):
    if _height == 0:
        _height = 1
    glViewport(0, 0, _width, _height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, _width, _height, 0.0, -1.0, 1.0)
    glMatrixMode(GL_MODELVIEW)

def InitGL():
    glClearColor(1.0, 1.0, 1.0, 0.0)
    glClearDepth(1.0)
    glShadeModel(GL_FLAT)

def keyPressed(*args):
    if args[0] == ESCAPE:
        sys.exit(0)

glutInit(sys.argv)
glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH | GLUT_MULTISAMPLE)
glutInitWindowSize(window_width, window_height)
glutInitWindowPosition(0, 0)
glutCreateWindow("")
glutDisplayFunc(DrawGLScene)
glutIdleFunc(DrawGLScene)
glutReshapeFunc(ReSizeGLScene)
glutKeyboardFunc(keyPressed)
InitGL()
ReSizeGLScene(window_width, window_height)
glutMainLoop()
