from orchestra import Orchestra
import unittest

class OrchestraTests(unittest.TestCase):
    def test_has_audio_extension(self):
        self.assertTrue(Orchestra._has_audio_extension('filename.mp3'))
        self.assertTrue(Orchestra._has_audio_extension('filename.flac'))
        self.assertTrue(Orchestra._has_audio_extension('filename.wav'))
        self.assertTrue(Orchestra._has_audio_extension('filename.WAV'))
        self.assertFalse(Orchestra._has_audio_extension('filename'))
        self.assertFalse(Orchestra._has_audio_extension('filename.avi'))
