import unittest
from stairs_step_is_partition import Stairs

class Step:
    def __init__(self, byte_offset, byte_size):
        self.byte_offset = byte_offset
        self.byte_size = byte_size
        self.byte_end = byte_offset + byte_size

    def __repr__(self):
        return "Step(byte_offset=%s, byte_end=%s)" % (self.byte_offset, self.byte_end)

class Segment:
    def __init__(self, begin, end):
        self.torrent_begin = begin
        self.torrent_end = end

    def __eq__(self, other):
        return (self.torrent_begin, self.torrent_end) == (
            other.torrent_begin, other.torrent_end)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "Segment(%s, %s)" % (self.torrent_begin, self.torrent_end)

class Args:
    waveform = False
    sync = False
    width = 500
    height = 500
    show_fps = False
    export = False
    osc_log = None
    waveform_gain = 1
    camera_script = None

stairs = Stairs(Args())

class split_at_step_boundaries_test(unittest.TestCase):
    def test_no_split_desired(self):
        self.given_steps([(0, 10),
                          (10, 10)])
        self.given_gathered([(3, 4)])
        self.expect_result([(3, 4)])

    def test_piece_overlaps_two_steps(self):
        self.given_steps([(0, 10),
                          (10, 10)])
        self.given_gathered([(9, 11)])
        self.expect_result([(9, 10),
                            (10, 11)])

    def test_completed_transmission(self):
        self.given_steps([(0, 10),
                          (10, 10)])
        self.given_gathered([(0, 20)])
        self.expect_result([(0, 10),
                            (10, 20)])

    def given_steps(self, steps_info):
        stairs._steps = [Step(offset, size) for offset,size in steps_info]

    def given_gathered(self, pieces_info):
        self._pieces = [Segment(begin, end) for begin,end in pieces_info]

    def expect_result(self, expected_segments_info):
        expected_segments = [Segment(begin, end) for begin,end in expected_segments_info]
        actual_segments = stairs._split_segments_at_step_boundaries(self._pieces)
        self.assertEquals(expected_segments, actual_segments)
