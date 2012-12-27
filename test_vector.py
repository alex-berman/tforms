from vector import Vector2d
import unittest
import math

class Vector2dTest(unittest.TestCase):
    def test_eq(self):
        self.assertTrue(Vector2d(0, 0) == Vector2d(0, 0))

    def test_inplace_add(self):
        v = Vector2d(2, 3)
        v += Vector2d(10, 20)
        self.assertEquals(Vector2d(12, 23), v)

    def test_add(self):
        v1 = Vector2d(2, 3)
        v2 = Vector2d(10, 20)
        self.assertEquals(Vector2d(12, 23), v1 + v2)

    def test_index(self):
        v = Vector2d(2, 3)
        self.assertEquals(2, v[0])
        self.assertEquals(3, v[1])

    def test_get_x(self):
        v = Vector2d(2, 3)
        self.assertEquals(2, v.x)

    def test_set_x(self):
        v = Vector2d(2, 3)
        v.x = 5
        self.assertEquals(Vector2d(5, 3), v)

    def test_equals_none(self):
        self.assertEquals(False, Vector2d(0,0) == None)

    def test_rotate(self):
        v = Vector2d(1, 0)
        w = v.rotate(-math.pi/2)
        self.assertAlmostEqual(0, w.x)
        self.assertAlmostEqual(-1, w.y)

    def test_inplace_mul(self):
        v = Vector2d(2, 3)
        v *= 10
        self.assertEquals(Vector2d(20, 30), v)
