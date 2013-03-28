from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import sys
sys.path.append("..")
from vector import Vector2d, DirectionalVector

window_width = 600
window_height = 600
ESCAPE = '\033'
COLUMNS = 20
ROWS = 20
ZOOM_POINT = Vector2d(0.5, 0.01)
ZOOM_FACTOR = 0.8

def DrawGLScene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    glColor3f(0,0,0)
    glPointSize(5)
    glBegin(GL_POINTS)
    for x in range(COLUMNS):
        for y in range(ROWS):
            p = Vector2d(float(x+0.5) / COLUMNS,
                         float(y+0.5) / ROWS)
            q = barrel_distort(p)
            glVertex2f(q.x * window_width, q.y * window_height)
    glEnd()

    glutSwapBuffers()

def barrel_distort(p):
    diff = p - ZOOM_POINT
    angle = diff.angle()
    mag = diff.mag()
    vicinity_to_edge = 1 - min([p.x, 1-p.x, p.y, 1-p.y])
    distorted_mag = pow(mag, ZOOM_FACTOR + (1 - ZOOM_FACTOR) * pow(vicinity_to_edge, 10.0))
    return DirectionalVector(angle.get(), distorted_mag) + ZOOM_POINT

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
    glShadeModel(GL_SMOOTH)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

def keyPressed(*args):
    if args[0] == ESCAPE:
        sys.exit(0)

glutInit(sys.argv)
glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
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
