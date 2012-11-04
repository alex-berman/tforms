import unittest
from gatherer import Gatherer

class File:
    def __init__(self, offset, length):
        self.offset = offset
        self.length = length

default_file = File(0, 100000000)

class Piece:
    def __init__(self, begin, end, f=None):
        if f is None:
            f = default_file
        self.begin = begin
        self.end = end
        self.f = f
        self.torrent_begin = self.begin + f.offset
        self.torrent_end = self.end + f.offset

    def __eq__(self, other):
        return self.begin == other.begin and \
            self.end == other.end and \
            self.torrent_begin == other.torrent_begin and \
            self.torrent_end == other.torrent_end

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'Piece(begin=%s, end=%s, torrent_begin=%s, torrent_end=%s)' % (
            self.begin, self.end, self.torrent_begin, self.torrent_end)

    def append(self, other):
        self.end = other.end

    def prepend(self, other):
        self.begin = other.begin

    def __hash__(self):
        return hash((self.begin, self.end))

    def joinable_with(self, other):
        return True

class PieceTest(unittest.TestCase):
    def test_eq(self):
        self.assertEquals(Piece(10, 20),
                          Piece(10, 20))

    def test_not_eq(self):
        self.assertTrue(Piece(10, 20) != Piece(11, 20))

class GathererTest(unittest.TestCase):
    def test_add_first_piece(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        expected_pieces = [Piece(10, 20)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_add_second_piece(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(40, 50))
        expected_pieces = [Piece(10, 20),
                           Piece(40, 50)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_append(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(40, 50))
        gatherer.add(Piece(20, 30))
        expected_pieces = [Piece(10, 30),
                           Piece(40, 50)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_prepend(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(40, 50))
        gatherer.add(Piece(30, 40))
        expected_pieces = [Piece(10, 20),
                           Piece(30, 50)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_fit_hole(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(40, 50))
        gatherer.add(Piece(20, 40))
        expected_pieces = [Piece(10, 50)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_overlap_begin(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(0, 15))
        expected_pieces = [Piece(0, 20)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_overlap_end(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(15, 30))
        expected_pieces = [Piece(10, 30)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_overlap_multiple_pieces(self):
        gatherer = Gatherer()
        gatherer.add(Piece(10, 20))
        gatherer.add(Piece(30, 40))
        gatherer.add(Piece(0, 50))
        expected_pieces = [Piece(0, 50)]
        self.assertEquals(expected_pieces, gatherer.pieces())

    def test_multiple_files_append(self):
        f1 = File(offset=0, length=30)
        f2 = File(offset=30, length=20)
        gatherer = Gatherer()
        gatherer.add(Piece(20, 30, f1))
        gatherer.add(Piece(0, 10, f2))
        expected_pieces = [Piece(20, 40, f1)]
        self.assertEquals(expected_pieces, gatherer.pieces())
