import unittest
import numpy
from audio_buffer import AudioBuffer

class AudioBufferTests(unittest.TestCase):
    SAMPLE_RATE = 44100

    def test_construction(self):
        frames = numpy.array([0.5, -0.5,
                              0.1, -0.1,
                              0.3, -0.3])
        b = AudioBuffer(self.SAMPLE_RATE, frames)
    
    def test_apply_pan(self):
        frames = numpy.array([0.5, -0.5,
                              0.1, -0.1,
                              0.3, -0.3,
                              0.4, -0.4])
        b = AudioBuffer(self.SAMPLE_RATE, frames)
        b.apply_pan_right_to_left()
        expected_frames = numpy.array([0.5 * 0,    -0.5 * 1,
                                       0.1 * 0.25, -0.1 * 0.75,
                                       0.3 * 0.5,  -0.3 * 0.5,
                                       0.4 * 0.75, -0.4 * 0.25])
        self.assertEqual(str(expected_frames), str(b.frames))

    def test_pan_env(self):
        frames = numpy.array([0, 0,
                              0, 0,
                              0, 0,
                              0, 0])
        b = AudioBuffer(self.SAMPLE_RATE, frames)
        expected_env = numpy.array([0,    1,
                                    0.25, 0.75,
                                    0.5,  0.5,
                                    0.75, 0.25])
        self.assertEquals(str(expected_env), str(b._pan_env()))

if __name__ == '__main__':
    unittest.main()
