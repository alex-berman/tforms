from ancestry_tracker import *
from ancestry_plotter import *
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
        self.assertEquals(0, len(last_piece.parents))

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

    def test_growth_preserves_parenthood(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0},

                {'id': 3, 'begin': 600, 'end': 700, 't': 30.0},

                {'id': 4, 'begin': 500, 'end': 600, 't': 40.0},


                {'id': 5, 'begin': 700, 'end': 800, 't': 40.0},
                ])
        last_piece = self.last_tracked_piece()
        self.assertEquals(set([20.0, 30.0]),
                          set([parent.t for parent in last_piece.parents.values()]))

    def test_growth_tracking(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0}
                ])
        last_piece = self.last_tracked_piece()
        expected_growth = [
            {'begin': 100, 'end': 200, 't': 0.0},
            {'begin': 100, 'end': 400, 't': 10.0}
            ]
        self.assert_growth(expected_growth, last_piece.growth)



    def given_chunks(self, chunks):
        self.chunks = chunks

    def last_tracked_piece(self):
        tracker = AncestryTracker()
        for chunk in self.chunks:
            tracker.add(Piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"]))
        self.assertEquals(1, len(tracker.last_pieces()))
        return tracker.last_pieces()[0]

    def assert_growth(self, expected_growth_as_dicts, actual_growth):
        self.assertEquals(len(expected_growth_as_dicts),
                          len(actual_growth))
        for (expected_piece_as_dict, actual_piece) in zip(
            expected_growth_as_dicts, actual_growth):
            self.assertEquals(expected_piece_as_dict["begin"],
                              actual_piece.begin)
            self.assertEquals(expected_piece_as_dict["end"],
                              actual_piece.end)
            self.assertEquals(expected_piece_as_dict["t"],
                              actual_piece.t)


class AncestryPlotterTest(unittest.TestCase):
    def test_lines_from_child_to_parents(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 400, 't': 10.0},
                {'id': 2, 'begin': 400, 'end': 500, 't': 20.0},

                {'id': 3, 'begin': 600, 'end': 700, 't': 30.0},

                {'id': 4, 'begin': 500, 'end': 600, 't': 40.0},
                ])
        self.when_plotted()
        self.expect_plotted_lines([
                (40.0, (100+700)/2,
                 20.0, (100+500)/2),
                (40.0, (100+700)/2,
                 30.0, (600+700)/2)
                ])

    def test_growth_paths(self):
        self.given_chunks([
                {'id': 0, 'begin': 100, 'end': 200, 't': 0.0},
                {'id': 1, 'begin': 200, 'end': 300, 't': 10.0},
                {'id': 2, 'begin': 300, 'end': 400, 't': 20.0},

                {'id': 3, 'begin': 500, 'end': 600, 't': 30.0},
                {'id': 4, 'begin': 600, 'end': 700, 't': 40.0},
                {'id': 5, 'begin': 700, 'end': 800, 't': 50.0},

                {'id': 6, 'begin': 900, 'end':1000, 't': 60.0},
                {'id': 7, 'begin':1000, 'end':1100, 't': 70.0},
                {'id': 8, 'begin':1100, 'end':1200, 't': 80.0},

                {'id': 9, 'begin': 400, 'end': 500, 't': 90.0},

                {'id':10, 'begin': 800, 'end': 900, 't':100.0},
                ])
        self.when_plotted()
        self.expect_plotted_paths([
                [(80.0, (900+1200)/2),
                 (70.0, (900+1100)/2),
                 (60.0, (900+1000)/2)],

                [(50.0, (500+800)/2),
                 (40.0, (500+700)/2),
                 (30.0, (500+600)/2)],

                [(20.0, (100+400)/2),
                 (10.0, (100+300)/2),
                 ( 0.0, (100+200)/2)]
                ])



    def given_chunks(self, chunks):
        self.chunks = chunks

    def when_plotted(self):
        class TestedAncestryPlotter(AncestryPlotter):
            def __init__(self, chunks):
                mockup_duration = 1
                total_size = \
                    max([chunk["end"] for chunk in chunks]) - \
                    min([chunk["begin"] for chunk in chunks])
                AncestryPlotter.__init__(self, total_size, mockup_duration, MockupOptions())
                for chunk in chunks:
                    self.add_piece(chunk["id"],
                                   chunk["t"],
                                   chunk["begin"],
                                   chunk["end"])

            def draw_line(self, t1, b1, t2, b2):
                self.plotted_lines.append((t1, b1, t2, b2))

            def draw_path(self, path):
                self.plotted_paths.append(path)

            def _rect_position(self, t, byte_pos):
                return Vector2d(t, byte_pos)

            def _override_recursion_limit(self): pass

        class MockupOptions:
            width = 1
            height = 1
            unit = "px"
            output_type = "svg"
            edge_style = LINE
            stroke_style = PLAIN
            geometry = RECT
            stroke_width = 1

        self.plotter = TestedAncestryPlotter(self.chunks)
        self.plotter.plotted_lines = []
        self.plotter.plotted_paths = []
        self.plotter.plot()

    def expect_plotted_lines(self, expected_lines):
        self.assertEqual(sorted(expected_lines), sorted(self.plotter.plotted_lines))

    def expect_plotted_paths(self, expected_paths):
        self.assertEqual(sorted(expected_paths), sorted(self.plotter.plotted_paths))
