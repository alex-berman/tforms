import math

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __ne__(self, other):
        return not (self == other)

    def __add__(self, other):
        return Vector(self.x + other.x,
                      self.y + other.y)
    
    def __sub__(self, other):
        return Vector(self.x - other.x,
                      self.y - other.y)

    def __mul__(self, factor):
        return Vector(self.x * factor,
                      self.y * factor)

    def __div__(self, factor):
        return Vector(self.x / factor,
                      self.y / factor)

    def __imul__(self, factor):
        self.x *= factor
        self.y *= factor
        return self

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __neg__(self):
        return self * (-1)

    def mag(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self):
        m = self.mag()
        self.x /= m
        self.y /= m

    def limit(self, desired_magnitude):
        m = self.mag()
        if m > desired_magnitude:
            self *= desired_magnitude / m

    def __repr__(self):
        return 'Vector(%s, %s)' % (self.x, self.y)

class DirectionalVector(Vector):
    def __init__(self, angle, magnitude):
        Vector.__init__(self,
                        math.cos(angle) * magnitude,
                        math.sin(angle) * magnitude)
