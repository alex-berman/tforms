from vector import Vector
import unittest

class VectorTest(unittest.TestCase):
    def test_eq(self):
        self.assertTrue(Vector(0, 0) == Vector(0, 0))

    def test_inplace_add(self):
        v = Vector(2, 3)
        v += Vector(10, 20)
        self.assertEquals(Vector(12, 23), v)
