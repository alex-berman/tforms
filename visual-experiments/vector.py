import math

class Angle:
    def __init__(self, value):
        self.value = self._clamp(value)

    def get(self):
        return self.value

    def __add__(self, other):
        return Angle(self.value + other.get())

    def __sub__(self, other):
        other_value = other.get()
        if abs(self.value - other_value) < math.pi:
            return Angle(self.value - other_value)
        elif self.value > other_value:
            return Angle(-2*math.pi - self.value + other_value)
        else:
            return Angle(2*math.pi + self.value - other_value)

    def __mul__(self, factor):
        return Angle(self.value * factor)

    def __iadd__(self, other):
        self.value = self._clamp(self.value + other.get())
        return self

    def _clamp(self, x):
        while x < 0:
            x += 2*math.pi
        while x > 2*math.pi:
            x -= 2*math.pi
        return x

    def __repr__(self):
        return "Angle(%s)" % self.value

        
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        try:
            return self.x == other.x and self.y == other.y
        except AttributeError:
            return False

    def __ne__(self, other):
        return not (self == other)

    def __add__(self, other):
        return Vector(self.x + other.x,
                      self.y + other.y)

    def __radd__(self, value):
        return Vector(self.x + value,
                      self.y + value)
    
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

    def set(self, other):
        self.x = other.x
        self.y = other.y

    def angle(self):
        return Angle(math.atan2(self.y, self.x))

    def __repr__(self):
        return 'Vector(%s, %s)' % (self.x, self.y)

class DirectionalVector(Vector):
    def __init__(self, angle, magnitude):
        Vector.__init__(self,
                        math.cos(angle) * magnitude,
                        math.sin(angle) * magnitude)
