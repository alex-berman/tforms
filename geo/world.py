import re
import gps

class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._gps = gps.GPS(width, height)
        self._load()

    def _load(self):
        f = open('world.dat', 'r')

        self.paths = []
        self._path = []

        for line in f:
            m = re.search('([\-0-9.]+)[\t ]+([\-0-9.]+)', line)
            if m:
                longitude = float(m.group(1))
                latitude = float(m.group(2))
                x = self._gps.x(longitude)
                y = self._gps.y(latitude)
                self._path.append((x, y))
            else:
                self._close_path()
        self._close_path()

        f.close()

    def _close_path(self):
        if len(self._path) > 0:
            self.paths.append(self._path)
        self._path = []
