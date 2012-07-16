from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import liblo
sys.path.append("..")
from orchestra import VISUALIZER_PORT

ESCAPE = '\033'

def handle_chunk(path, args, types, src, data):
    print "received message '%s'" % path

def setup_osc():
    global server
    server = liblo.Server(VISUALIZER_PORT)
    server.add_method("/chunk", "ifff", handle_chunk)

    
def InitGL(Width, Height):
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClearDepth(1.0)
    glDepthFunc(GL_LESS)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
	
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)

def ReSizeGLScene(Width, Height):
    if Height == 0:
	    Height = 1

    glViewport(0, 0, Width, Height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

def DrawGLScene():
    global server
    server.recv(10)

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()					# Reset The View 

    # Move Left 1.5 units and into the screen 6.0 units.
    glTranslatef(-1.5, 0.0, -6.0)

    # Draw a triangle
    glBegin(GL_POLYGON)                 # Start drawing a polygon
    glVertex3f(0.0, 1.0, 0.0)           # Top
    glVertex3f(1.0, -1.0, 0.0)          # Bottom Right
    glVertex3f(-1.0, -1.0, 0.0)         # Bottom Left
    glEnd()                             # We are done with the polygon


    # Move Right 3.0 units.
    glTranslatef(3.0, 0.0, 0.0)

    # Draw a square (quadrilateral)
    glBegin(GL_QUADS)                   # Start drawing a 4 sided polygon
    glVertex3f(-1.0, 1.0, 0.0)          # Top Left
    glVertex3f(1.0, 1.0, 0.0)           # Top Right
    glVertex3f(1.0, -1.0, 0.0)          # Bottom Right
    glVertex3f(-1.0, -1.0, 0.0)         # Bottom Left
    glEnd()                             # We are done with the polygon

    glutSwapBuffers()

def keyPressed(*args):
    if args[0] == ESCAPE:
	    sys.exit()

def main():
	global window
        setup_osc()
	glutInit(sys.argv)
	glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
	glutInitWindowSize(640, 480)
	glutInitWindowPosition(0, 0)
	window = glutCreateWindow("")
	glutDisplayFunc(DrawGLScene)
	glutIdleFunc(DrawGLScene)
	glutReshapeFunc(ReSizeGLScene)
	glutKeyboardFunc(keyPressed)
	InitGL(640, 480)
	glutMainLoop()

print "Hit ESC key to quit."
main()
    	
