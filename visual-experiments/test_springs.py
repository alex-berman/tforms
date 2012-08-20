from springs import spring_force
from vector import Vector2d
import unittest

class SpringsTest(unittest.TestCase):
    def test_attraction_right(self):
        source = Vector2d(0,0)
        target = Vector2d(10,0)
        desired_distance = 3
        expected_force = Vector2d(7,0)
        self.assertEquals(desired_distance, (source + expected_force - target).mag())
        self.assertEquals(expected_force, spring_force(source, target, desired_distance))

    def test_attraction_up(self):
        source = Vector2d(0,0)
        target = Vector2d(0,10)
        desired_distance = 3
        expected_force = Vector2d(0,7)
        self.assertEquals(desired_distance, (source + expected_force - target).mag())
        self.assertEquals(expected_force, spring_force(source, target, desired_distance))

    def test_attraction_left(self):
        source = Vector2d(0,0)
        target = Vector2d(-10,0)
        desired_distance = 3
        expected_force = Vector2d(-7,0)
        self.assertEquals(desired_distance, (source + expected_force - target).mag())
        self.assertEquals(expected_force, spring_force(source, target, desired_distance))

    def test_repulsion_left(self):
        source = Vector2d(0,0)
        target = Vector2d(3,0)
        desired_distance = 10
        expected_force = Vector2d(-7,0)
        self.assertEquals(desired_distance, (source + expected_force - target).mag())
        self.assertEquals(expected_force, spring_force(source, target, desired_distance))

