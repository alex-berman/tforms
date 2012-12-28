from envelope import AdsrEnvelope
import unittest

class AdsrEnvelopeTest(unittest.TestCase):
    def test_default_is_constant_at_1(self):
        env = AdsrEnvelope()
        self.assertAlmostEquals(1.0, env.value(0.0))
        self.assertAlmostEquals(1.0, env.value(10.0))
        self.assertAlmostEquals(1.0, env.value(100.0))

    def test_decay_to_0(self):
        env = AdsrEnvelope(attack=0, decay=3, sustain=0)
        self.assertAlmostEquals(1.0, env.value(0.0))
        self.assertAlmostEquals(0.5, env.value(1.5))
        self.assertAlmostEquals(0.0, env.value(3.0))
        self.assertAlmostEquals(0.0, env.value(10.0))

    def test_attack_and_stay_at_1(self):
        env = AdsrEnvelope(attack=3, decay=0, sustain=1)
        self.assertAlmostEquals(0.0, env.value(0.0))
        self.assertAlmostEquals(0.5, env.value(1.5))
        self.assertAlmostEquals(1.0, env.value(3.0))
        self.assertAlmostEquals(1.0, env.value(10.0))

    def test_attack_and_decay(self):
        env = AdsrEnvelope(attack=1, decay=3, sustain=0.5)
        self.assertAlmostEquals(0.0,  env.value(0.0))
        self.assertAlmostEquals(0.5,  env.value(0.5))
        self.assertAlmostEquals(1.0,  env.value(1.0))
        self.assertAlmostEquals(0.75, env.value(2.5))
        self.assertAlmostEquals(0.5,  env.value(4.0))
        self.assertAlmostEquals(0.5,  env.value(4.5))
        self.assertAlmostEquals(0.5,  env.value(10))
