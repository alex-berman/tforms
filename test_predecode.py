import predecode
import unittest

class PredecoderTests(unittest.TestCase):
    def setUp(self):
        tr_log = None
        location = None
        self.predecoder = predecode.Predecoder(tr_log, location)

    def test_target_filename(self):
        self.assertEquals('filename.wav',
                          self.predecoder._target_filename('filename.mp3'))
        self.assertEquals('filename.wav',
                          self.predecoder._target_filename('filename.flac'))

    def test_extension(self):
        self.assertEquals('mp3',
                          self.predecoder._extension('filename.mp3'))
        self.assertEquals('mp3',
                          self.predecoder._extension('filename.MP3'))

    def test_decodable(self):
        self.assertTrue(self.predecoder._decodable('filename.mp3'))
        self.assertTrue(self.predecoder._decodable('filename.flac'))
        self.assertFalse(self.predecoder._decodable('filename'))
        self.assertFalse(self.predecoder._decodable('filename.avi'))
