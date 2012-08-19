from interpret import Interpreter
import unittest

class InterpretTestCase(unittest.TestCase):
    def test_single_chunk_gets_unadjusted_rate(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
        self.given_chunks(
            [{"t": 0,
              "begin": 0, "end": 1000}])
        self.assert_interpretation(
            [{"onset": 0,
              "begin": 0, "end": 1000,
              "duration": 2.0*0.1}])

    def test_consecutive_chunks_are_joined_and_rate_adjusted(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
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
              "duration": 0.5}])

    def test_non_consecutive_chunks_are_divided_into_different_segments(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
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
              "duration": 0.1},
             {"onset": 0.5,
              "begin": 5000, "end": 7000,
              "duration": 0.2}])

    def test_chunks_from_different_peers_are_not_joined(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
        self.given_chunks(
            [{"peeraddr": "10.0.0.1",
              "t": 0,
              "begin": 0, "end": 1000},
             {"peeraddr": "10.0.0.2",
              "t": 0.3,
              "begin": 1000, "end": 2000}])
        self.assert_interpretation_length(2)

    def test_chunks_from_different_files_are_not_joined(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000},
                          {"duration": 3.0,
                           "length": 15000}])
        self.given_chunks(
            [{"filenum": 0,
              "t": 0,
              "begin": 0, "end": 1000},
             {"filenum": 1,
              "t": 0.3,
              "begin": 1000, "end": 2000}])
        self.assert_interpretation_length(2)

    def test_grouping_tolerates_interwoven_peers(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
        self.given_chunks(
            [{"peeraddr": "10.0.0.1",
              "t": 0,
              "begin": 0, "end": 1000},
             {"peeraddr": "20.0.0.1",
              "t": 0.1,
              "begin": 5000, "end": 6000},
             {"peeraddr": "10.0.0.1",
              "t": 0.5,
              "begin": 1000, "end": 2000},
             {"peeraddr": "20.0.0.1",
              "t": 0.6,
              "begin": 6000, "end": 7000},
             ])

        self.assert_interpretation(
            [{"peeraddr": "10.0.0.1",
              "onset": 0,
              "begin": 0, "end": 2000,
              "duration": 0.5},
             {"peeraddr": "20.0.0.1",
              "onset": 0.1,
              "begin": 5000, "end": 7000,
              "duration": 0.5},
             ])

    def test_chunks_separated_by_long_pause_are_not_joined(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
        self.given_chunks(
            [{"filenum": 0,
              "t": 0,
              "begin": 0, "end": 1000},
             {"filenum": 0,
              "t": 10,
              "begin": 1000, "end": 2000}])
        self.assert_interpretation_length(2)

    def test_simulataneous_chunks_do_not_yield_zero_duration(self):
        self.given_files([{"duration": 2.0,
                           "length": 10000}])
        self.given_chunks(
            [{"t": 0,
              "begin": 0, "end": 1000},
             {"t": 0,
              "begin": 1000, "end": 2000}])
        self.assert_interpretation(
            [{"onset": 0,
              "begin": 0, "end": 2000,
              "duration": 2.0*0.2}])


    def setUp(self):
        self.interpreter = Interpreter()

    def given_files(self, files):
        self.files = files

    def given_chunks(self, chunks):
        self.chunks = map(self._set_filenum_and_peer, chunks)

    def _set_filenum_and_peer(self, chunk):
        if not "filenum" in chunk:
            chunk["filenum"] = 0
        if not "peeraddr" in chunk:
            chunk["peeraddr"] = "10.0.0.1"
        if not "id" in chunk:
            chunk["id"] = 0
        return chunk

    def assert_interpretation(self, expected_score):
        actual_score = self.interpreter.interpret(self.chunks, self.files)
        expected_score = map(self._replace_durations_with_float_comparable_instances,
                             expected_score)
        expected_score = map(self._fill_potential_gaps_with_actual_values,
                             zip(expected_score, actual_score))
        self.assertEquals(expected_score, actual_score)

    def _replace_durations_with_float_comparable_instances(self, segment):
        segment["duration"] = Duration(segment["duration"])
        return segment

    def _fill_potential_gaps_with_actual_values(self, (expected_dict_pattern, actual_dict)):
        expected_dict = {}
        for key, actual_value in actual_dict.iteritems():
            if key in expected_dict_pattern:
                expected_dict[key] = expected_dict_pattern[key]
            else:
                expected_dict[key] = actual_value
        return expected_dict

    def assert_interpretation_length(self, expected_length):
        actual_score = self.interpreter.interpret(self.chunks, self.files)
        self.assertEquals(expected_length, len(actual_score))

    maxDiff = 1000


class Duration:
    PRECISION = 0.000001

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, Duration):
            return abs(self.value - other.value) < self.PRECISION
        elif isinstance(other, float):
            return abs(self.value - other) < self.PRECISION
        else:
            return False

    def __repr__(self):
        return "Duration(%s)" % self.value
