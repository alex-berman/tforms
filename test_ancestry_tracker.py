from ancestry_tracker import *
import unittest

class AncestryTrackerTest(unittest.TestCase):
    def test_straight_lineage(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0}
                ])
        last_piece = self.last_tracked_piece()
        self.assertEquals(20, last_piece.t)
        self.assertEquals(100, last_piece.begin)
        self.assertEquals(500, last_piece.end)
        self.assertEquals(1, len(last_piece.parents))

    def test_2_generations(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0},

                {'id': 3, 'begin': 600, 'end': 700, 't': 30.0},

                {'id': 4, 'begin': 500, 'end': 600, 't': 40.0},
                ])
        last_piece = self.last_tracked_piece()
        self.assertEquals(40.0, last_piece.t)
        self.assertEquals(100, last_piece.begin)
        self.assertEquals(700, last_piece.end)
        self.assertEquals(set([20.0, 30.0]),
                          set([parent.t for parent in last_piece.parents.values()]))

    def test_3_generations(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0},

                {'id': 3, 'begin': 600, 'end': 700, 't': 30.0},

                {'id': 4, 'begin': 500, 'end': 600, 't': 40.0},


                {'id':10, 'begin':1100, 'end':1200, 't':100.0},
                {'id':11, 'begin':1200, 'end':1400, 't':110.0},
                {'id':12, 'begin':1400, 'end':1500, 't':120.0},

                {'id':13, 'begin':1600, 'end':1700, 't':130.0},

                {'id':14, 'begin':1500, 'end':1600, 't':140.0},


                {'id':15, 'begin': 700, 'end':1100, 't':200.0},
                ])
        last_piece = self.last_tracked_piece()
        self.assertEquals(200.0, last_piece.t)
        self.assertEquals(100, last_piece.begin)
        self.assertEquals(1700, last_piece.end)
        self.assertEquals(set([40.0, 140.0]),
                          set([parent.t for parent in last_piece.parents.values()]))

        parent1 = filter(lambda parent: parent.t == 40, last_piece.parents.values())[0]
        self.assertEquals(100, parent1.begin)
        self.assertEquals(700, parent1.end)
        self.assertEquals(set([20.0, 30.0]),
                          set([parent.t for parent in parent1.parents.values()]))

        parent2 = filter(lambda parent: parent.t == 140, last_piece.parents.values())[0]
        self.assertEquals(1100, parent2.begin)
        self.assertEquals(1700, parent2.end)
        self.assertEquals(set([120.0, 130.0]),
                          set([parent.t for parent in parent2.parents.values()]))

    def given_chunks(self, chunks):
        self.chunks = chunks

    def last_tracked_piece(self):
        tracker = AncestryTracker()
        for chunk in self.chunks:
            tracker.add(Piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"]))
        self.assertEquals(1, len(tracker.last_pieces()))
        return tracker.last_pieces()[0]
