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

    def __imul__(self, factor):
        self.x *= factor
        self.y *= factor
        return self

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

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self
