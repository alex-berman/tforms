import unittest
from gatherer import Gatherer

class Piece:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __eq__(self, other):
        return self.begin == other.begin and \
            self.end == other.end

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'Piece(%s, %s)' % (self.begin, self.end)

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
        piece = Piece(11, 20)
        piece.begin = 10
        self.assertFalse(Piece(10, 20) != piece)

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
