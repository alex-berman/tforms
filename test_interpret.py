from interpret import Interpretor, Duration
import unittest

class InterpretTestCase(unittest.TestCase):
    def test_single_chunk_gets_unadjusted_rate(self):
        self.given_file_duration(2.0)
        self.given_file_size(10000)
        self.given_chunks(
            [{"t": 0,
              "begin": 0, "end": 1000}])
        self.assert_interpretation(
            [{"onset": 0,
              "begin": 0, "end": 1000,
              "duration": Duration(2.0*0.1)}])

    def test_consecutive_chunks_are_joined_and_rate_adjusted(self):
        self.given_file_duration(2.0)
        self.given_chunks(
            [{"t": 0,
              "begin": 0, "end": 1000},
             {"t": 0.3,
              "begin": 1000, "end": 2000},
             {"t": 0.5,
              "begin": 2000, "end": 3000}])
        self.assert_interpretation(
            [{"onset": 0,
              "begin": 0, "end": 3000,
              "duration": Duration(0.5)}])

    def test_non_consecutive_chunks_are_divided_into_different_sounds(self):
        self.given_file_duration(2.0)
        self.given_chunks(
            [{"t": 0,
              "begin": 0, "end": 1000},
             {"t": 0.1,
              "begin": 1000, "end": 2000},
             {"t": 0.5,
              "begin": 5000, "end": 6000},
             {"t": 0.7,
              "begin": 6000, "end": 7000},
             ])
        self.assert_interpretation(
            [{"onset": 0,
              "begin": 0, "end": 2000,
              "duration": Duration(0.1)},
             {"onset": 0.5,
              "begin": 5000, "end": 7000,
              "duration": Duration(0.2)}])

    def setUp(self):
        self.interpretor = Interpretor()
        self.files = [{"offset": 0}]

    def given_file_duration(self, duration):
        self.files[0]["duration"] = duration

    def given_file_size(self, size):
        self.files[0]["length"] = size

    def given_chunks(self, chunks):
        self.chunks = map(self._set_filenum, chunks)

    def _set_filenum(self, chunk):
        chunk["filenum"] = 0
        return chunk

    def assert_interpretation(self, expected):
        actual = self.interpretor.interpret(self.chunks, self.files)
        self.assertEquals(expected, actual)
