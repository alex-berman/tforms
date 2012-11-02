from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys
import math

window_width = 300
window_height = 300
ESCAPE = '\033'

NUM_SAMPLES = 8
gpJitter = [
	(-0.334818,  0.435331),
	( 0.286438, -0.393495),
	( 0.459462,  0.141540),
	(-0.414498, -0.192829),
	(-0.183790,  0.082102),
	(-0.079263, -0.317383),
	( 0.102254,  0.299133),
	( 0.164216, -0.054399)
]

def accFrustum(left, right, bottom, 
               top, near, far, pixdx, 
               pixdy, eyedx, eyedy, focus):
    xwsize = right - left
    ywsize = top - bottom

    dx = -(pixdx*xwsize/window_width + eyedx*near/focus)
    dy = -(pixdy*ywsize/window_height + eyedy*near/focus)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glFrustum (left + dx, right + dx, bottom + dy, top + dy, near, far)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef (-eyedx, -eyedy, 0.0)

def accPerspective(fovy, aspect,
                   near, far, pixdx, pixdy,
                   eyedx, eyedy, focus):
    fov2 = ((fovy*math.pi) / 180.0) / 2.0

    top = near / (math.cos(fov2) / math.sin(fov2))
    bottom = -top

    right = top * aspect
    left = -right

    accFrustum (left, right, bottom, top, near, far,
		pixdx, pixdy, eyedx, eyedy, focus)

def DrawGLScene():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_ACCUM_BUFFER_BIT)

    for jitter in range(NUM_SAMPLES):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        accPerspective (45.0, float(window_width)/window_height,
                        0.1, 100.0, gpJitter[jitter][0], gpJitter[jitter][1],
                        0.0, 0.0, 1.0)
        render()
        glAccum(GL_ACCUM, 1.0/NUM_SAMPLES)
    glAccum(GL_RETURN, 1.0)

    glFlush()
    glutSwapBuffers()

def render():
    glPushMatrix()
    glTranslatef(0, 0, -2)

    glColor3f(0,0,0)
    glBegin(GL_POLYGON)
    glVertex3f(-.10, .20, 0)
    glVertex3f(.50, .10, 0)
    glVertex3f(.50, .60, 0)
    glVertex3f(-.10, .50, 0)
    glEnd()

    glPopMatrix()

def ReSizeGLScene(_width, _height):
    if _height == 0:
        _height = 1
    glViewport(0, 0, _width, _height)
    window_width = _width
    window_height = _height

def InitGL():
    glClearColor(1.0, 1.0, 1.0, 0.0)
    glClearAccum(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glShadeModel(GL_FLAT)
    glDisable(GL_DEPTH_TEST)

def keyPressed(*args):
    if args[0] == ESCAPE:
        sys.exit(0)

glutInit(sys.argv)
glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH | GLUT_ACCUM)
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
