NUM_STEPS = 10
STAIRS_WIDTH = 1.0
STEP_HEIGHT = 0.1
STEP_DEPTH = 0.3
WALL_X = 0
CAMERA_X = 0
CAMERA_Y = -0.4
CAMERA_Z = -6.5

import visualizer
from OpenGL.GL import *
from OpenGL.GLU import *

class Stairs(visualizer.Visualizer):
    def __init__(self, args):
        visualizer.Visualizer.__init__(self, args)
        self.inner_x = WALL_X - STAIRS_WIDTH / 2
        self.outer_x = WALL_X + STAIRS_WIDTH / 2

    def render(self):
        self.draw_stairs_outline()

    def draw_stairs_outline(self):
        glLoadIdentity()
        glTranslatef(CAMERA_X, CAMERA_Y, CAMERA_Z)
        glColor3f(0,0,0)

        for n in range(NUM_STEPS):
            y1 = - n    * STEP_HEIGHT
            y2 = -(n+1) * STEP_HEIGHT
            z1 =  n    * STEP_DEPTH
            z2 = (n+1) * STEP_DEPTH

            glBegin(GL_LINE_LOOP)
            glVertex3f(self.inner_x, y1, z1)
            glVertex3f(self.inner_x, y2, z1)
            glVertex3f(self.outer_x, y2, z1)
            glVertex3f(self.outer_x, y1, z1)
            glEnd()

            glBegin(GL_LINE_LOOP)
            glVertex3f(self.inner_x, y2, z1)
            glVertex3f(self.inner_x, y2, z2)
            glVertex3f(self.outer_x, y2, z2)
            glVertex3f(self.outer_x, y2, z1)
            glEnd()

    def ReSizeGLScene(self, _width, _height):
        if _height == 0:
            _height = 1
        glViewport(0, 0, _width, _height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, float(_width) / _height, 0.1, 100)
        glMatrixMode(GL_MODELVIEW)

if __name__ == '__main__':
    visualizer.run(Stairs)
