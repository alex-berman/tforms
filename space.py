from decimal import *
import random

class StereoSpace:
    def __init__(self):
        self._nodes = []

    def add_node(self, position):
        self._nodes.append(position)
        self._nodes.sort()

    def position_with_max_distance_to_nodes(self):
        if len(self._nodes) == 0:
            return Decimal(random.uniform(0, 1))
        else:
            hypotheses = [Decimal('0'), Decimal('1')]
            hypotheses.extend(self._midpoints_between_nodes())
            return max(hypotheses, key=lambda x: self._distance_to_nearest_node(x))

    def _midpoints_between_nodes(self):
        result = []
        for i in range(0, len(self._nodes) - 1):
            midpoint = (self._nodes[i] + self._nodes[i+1]) / 2
            result.append(midpoint)
        return result

    def _distance_to_nearest_node(self, position):
        return min(map(lambda x: abs(position - x),
                       self._nodes))
