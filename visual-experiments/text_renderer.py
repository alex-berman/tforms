from OpenGL.GL import *
from OpenGL.GLUT import *
try:
    import FTGL
except ImportError:
    pass

class TextRenderer:
    def __init__(self, text, size, font=None, spacing=None):
        self.text = text
        self.size = size
        self.font = font
        self.spacing = spacing
        self.scale = 1

    def render(self, x, y, v_align="left", h_align="top"):
        width = self.get_width()
        glPushMatrix()
        glTranslatef(x, y, 0)
        glScalef(self.scale, self.scale, self.scale)
        if h_align == "right":
            glTranslatef(-width, 0, 0)
        if v_align == "top":
            glTranslatef(0, -self.size, 0)
        self.stroke()
        glPopMatrix()

class GlutTextRenderer(TextRenderer):
    TOP = 119.05 # http://www.opengl.org/resources/libraries/glut/spec3/node78.html
    BOTTOM = 33.33

    def __init__(self, *args):
        TextRenderer.__init__(self, *args)
        if not self.font:
            self.font = GLUT_STROKE_ROMAN
        self.scale = self.size / (self.TOP + self.BOTTOM)

    def stroke(self):
        glLineWidth(1.0)
        glPointSize(1.0)
        for c in self.text:
            if c == ' ' and self.spacing is not None:
                glTranslatef(self.spacing, 0, 0)
            else:
                glutStrokeCharacter(self.font, ord(c))

    def get_width(self):
        glPushMatrix()
        glScalef(self.scale, self.scale, self.scale)
        width = 0
        for c in self.text:
            if c == ' ' and self.spacing is not None:
                width += self.spacing
            else:
                width += glutStrokeWidth(self.font, ord(c))
        glPopMatrix()
        return width
