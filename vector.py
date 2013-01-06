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

    def __neg__(self):
        return Angle(-self.value)

    def __repr__(self):
        return "Angle(%s)" % self.value

        
class Vector:
    DIMENSIONS = {"x": 0,
                  "y": 1,
                  "z": 2}

    def __init__(self, n, v):
        self.n = n
        self.v = v

    def __eq__(self, other):
        try:
            return all([self[i] == other[i]
                        for i in range(self.n)])
        except (AttributeError, TypeError):
            return False

    def __getitem__(self, i):
        return self.v[i]

    def __setitem__(self, i, value):
        self.v[i] = value

    def __getattr__(self, attr):
        try:
            i = self.DIMENSIONS[attr]
            return self.v[i]
        except KeyError:
            raise AttributeError

    def __setattr__(self, attr, value):
        try:
            i = self.DIMENSIONS[attr]
            self.__dict__["v"][i] = value
        except KeyError:
            self.__dict__[attr] = value

    def __ne__(self, other):
        return not (self == other)

    def __add__(self, other):
        return Vector(self.n,
                      [self[i] + other[i]
                       for i in range(self.n)])

    def __radd__(self, value):
        return Vector(self.n,
                      [self[i] + value
                       for i in range(self.n)])
    
    def __sub__(self, other):
        return Vector(self.n,
                      [self[i] - other[i]
                       for i in range(self.n)])

    def __mul__(self, factor):
        return Vector(self.n,
                      [self[i] * factor
                       for i in range(self.n)])

    def __div__(self, factor):
        return Vector(self.n,
                      [self[i] / factor
                       for i in range(self.n)])

    def __imul__(self, factor):
        for i in range(self.n):
            self[i] *= factor
        return self

    def __iadd__(self, other):
        for i in range(self.n):
            self[i] += other[i]
        return self

    def __neg__(self):
        return self * (-1)

    def mag(self):
        return math.sqrt(sum([self[i]*self[i]
                              for i in range(self.n)]))

    def normalize(self):
        m = self.mag()
        for i in range(self.n):
            self[i] /= m

    def limit(self, desired_magnitude):
        m = self.mag()
        if m > desired_magnitude:
            self *= desired_magnitude / m

    def set(self, other):
        for i in range(self.n):
            self[i] = other[i]

    def angle(self):
        return Angle(math.atan2(self.y, self.x))

    def rotate(self, angle):
        new_angle = self.angle() + Angle(angle)
        return DirectionalVector(new_angle.get(), self.mag())

    def __repr__(self):
        return 'Vector(%s, %s)' % (self.n, self.v)

    def __hash__(self):
        return hash(tuple(self.v))

class Vector2d(Vector):
    def __init__(self, x, y):
        Vector.__init__(self, 2, [x,y])

class Vector3d(Vector):
    def __init__(self, x, y, z):
        Vector.__init__(self, 3, [x,y,z])

class DirectionalVector(Vector2d):
    def __init__(self, angle, magnitude):
        Vector2d.__init__(self,
                          math.cos(angle) * magnitude,
                          math.sin(angle) * magnitude)
