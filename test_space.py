from decimal import *
from space import StereoSpace
import unittest

class StereoSpaceTests(unittest.TestCase):
    def test_good_spread(self):
        self.space = StereoSpace()
        self.space.add_node(Decimal('.2'))
        self._next_position_is('1')
        self._next_position_is('.6')
        self._next_position_are(['0', '.4', '.8'])
        self._next_position_are(['.1', '.3', '.5', '.7', '.9'])

    def test_arbitrary_start_position(self):
        self.space = StereoSpace()
        arbitrary_start_position = self.space.position_with_max_distance_to_nodes()
        self.space.add_node(arbitrary_start_position)
        next_position = self.space.position_with_max_distance_to_nodes()

    def _next_position_is(self, expected_position):
        actual_position = self.space.position_with_max_distance_to_nodes()
        self.assertEquals(Decimal(expected_position), actual_position)
        self.space.add_node(actual_position)

    def _next_position_are(self, expected_positions_list):
        expected_positions = set(map(Decimal, expected_positions_list))
        while len(expected_positions) > 0:
            actual_position = self.space.position_with_max_distance_to_nodes()
            if actual_position not in expected_positions:
                raise Exception("did not expect position %r (expected %r, current nodes %r)" % (
                        actual_position, expected_positions, self.space._nodes))
            expected_positions.remove(actual_position)
            self.space.add_node(actual_position)
