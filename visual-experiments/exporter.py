from PIL import Image
from OpenGL.GL import *

class Exporter:
    def __init__(self, target_directory, x, y, width, height):
        self.target_directory = target_directory
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.frame_count = 0

    def export_frame(self):
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        buffer = glReadPixels(self.x, self.y, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        image = Image.fromstring(mode="RGB", size=(self.width, self.height), data=buffer)
        filename = "%s/%05d.png" % (self.target_directory, self.frame_count)
        image.save(filename)
        self.frame_count += 1
