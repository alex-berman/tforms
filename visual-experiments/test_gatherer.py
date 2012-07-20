import unittest
from gatherer import Gatherer

class Piece:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __eq__(self, other):
        return self.begin == other.begin and \
            self.end == other.end

    def __repr__(self):
        return 'Piece(%s, %s)' % (self.begin, self.end)

    def append(self, other):
        self.end = other.end

    def prepend(self, other):
        self.begin = other.begin

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
