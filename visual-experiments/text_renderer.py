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
        width, height = self.get_size()
        glPushMatrix()
        glTranslatef(x, y, 0)
        glScalef(self.scale, self.scale, self.scale)
        if h_align == "right":
            glTranslatef(-width, 0, 0)
        if v_align == "top":
            glTranslatef(0, -self.size, 0)
        self.stroke()
        #self._draw_bbox() # TEMP
        glPopMatrix()

    def bounding_box(self, x1, y1, v_align="left", h_align="top"):
        width, height = self.get_size()
        if h_align == "right":
            x1 -= width
        if v_align == "top":
            y1 -= self.size
        x2 = x1 + width
        y2 = y1 + height
        return x1, y1, x2, y2

    def _draw_bbox(self):
        width, height = self.get_size()
        glBegin(GL_LINE_LOOP)
        glVertex2f(0, 0)
        glVertex2f(width, 0)
        glVertex2f(width, height)
        glVertex2f(0, height)
        glEnd()

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

    def get_size(self):
        glPushMatrix()
        glScalef(self.scale, self.scale, self.scale)
        width = 0
        for c in self.text:
            if c == ' ' and self.spacing is not None:
                width += self.spacing
            else:
                width += glutStrokeWidth(self.font, ord(c))
        glPopMatrix()
        return width, self.size


ftgl_fonts = {}

class FtglTextRenderer(TextRenderer):
    RESOLUTION = 72

    def __init__(self, *args):
        TextRenderer.__init__(self, *args)
        if not self.font:
            raise Exception("font required")
        self._font_object = self._prepare_font(self.font)
        self.text = self.text.encode("utf8")

    def _prepare_font(self, name):
        try:
            return ftgl_fonts[name]
        except KeyError:
            font = FTGL.OutlineFont(name)
            font.FaceSize(int(self.size), self.RESOLUTION)
            ftgl_fonts[name] = font
            return font

    def stroke(self):
        glLineWidth(1.0)
        glPointSize(1.0)
        self._font_object.Render(self.text)

    def get_size(self):
        llx, lly, llz, urx, ury, urz = self._font_object.BBox(self.text)
        width = urx - llx
        height = ury - lly
        return width, height
