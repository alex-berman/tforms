import unittest
from dynamic_scope import DensityDrivenScope

class DensityDrivenScopeTest(unittest.TestCase):
    def test_non_updated_is_linear(self):
        scope = DensityDrivenScope(100)
        for x in range(100):
            self.assertAlmostEqual(float(x) / 100, scope.map(x))

    def test_one_event(self):
        scope = DensityDrivenScope(1.0, num_partitions=10, blur_radius=0)
        scope.update([0.15])
        self.assertLess(scope.map(0.09), 0.1)
        self.assertTrue(0.1 < scope.map(0.11) < 0.9)
        self.assertTrue(0.1 < scope.map(0.19) < 0.9)
        self.assertGreater(scope.map(0.21), 0.9)
