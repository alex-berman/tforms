import unittest
from layout_manager import LayoutManager1d

class LayoutManager1dTest(unittest.TestCase):
    def setUp(self):
        self.layout_manager = LayoutManager1d()

    def test_add_non_overlapping_components(self):
        self.assertTrue(self.layout_manager.add(0, 1))
        self.assertTrue(self.layout_manager.add(8, 9))
        self.assertTrue(self.layout_manager.add(3, 4))

    def test_cannot_add_if_overlapping_below(self):
        self.layout_manager.add(10, 20)
        self.assertFalse(self.layout_manager.add(5, 15))

    def test_cannot_add_if_overlapping_above(self):
        self.layout_manager.add(10, 20)
        self.assertFalse(self.layout_manager.add(15, 25))

    def test_cannot_add_if_overlapping_within(self):
        self.layout_manager.add(10, 20)
        self.assertFalse(self.layout_manager.add(15, 17))

    def test_remove(self):
        first_component = self.layout_manager.add(10, 20)
        self.layout_manager.remove(first_component)
        self.assertTrue(self.layout_manager.add(5, 15))
