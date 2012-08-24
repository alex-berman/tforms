#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-width", type=int, default=500)
parser.add_argument("-height", type=int, default=500)
parser.add_argument("-stroke_width", type=float, default=1)
options = parser.parse_args()

logfilename = "%s/session.log" % options.sessiondir
log = TrLogReader(logfilename, options.torrentname, options.filenum).get_log()
print >> sys.stderr, "found %d chunks" % len(log.chunks)

total_size = max([chunk["end"] for chunk in log.chunks])

def byte_to_y(byte_pos): return min(int(float(byte_pos) / total_size * options.height), options.height-1)

class Piece:
    def __init__(self, t, begin, end):
        self.t = t
        self.begin = begin
        self.end = end

class BranchingTracker:
    def __init__(self):
        self._pieces = dict()
        self._counter = 1
        self.branchings = []

    def add(self, new_piece):
        overlapping_pieces = self._overlapping_pieces(new_piece)
        if len(overlapping_pieces) > 0:
            if (len(overlapping_pieces) == 1 and
                self._pieces[overlapping_pieces[0]].end == new_piece.begin):
                appendable_piece = self._pieces[overlapping_pieces[0]]
                appendable_piece.branch["pieces"].append(new_piece)
                appendable_piece.end = new_piece.end
            else:
                new_extension = [new_piece]
                new_extension.extend([self._pieces[key] for key in overlapping_pieces])
                kept_overlapping_piece = self._pieces[overlapping_pieces.pop(0)]
                kept_overlapping_piece.begin = min([piece.begin for piece in new_extension])
                kept_overlapping_piece.end = max([piece.end for piece in new_extension])
                kept_overlapping_piece.byte_size = kept_overlapping_piece.end - kept_overlapping_piece.begin
                for key in overlapping_pieces:
                    overlapping_piece = self._pieces[key]
                    if overlapping_piece.branch:
                        overlapping_piece.branch["end_time"] = new_piece.t
                        overlapping_piece.branch["end"] = new_piece.end
                    del self._pieces[key]
        else:
            self._pieces[self._counter] = new_piece
            new_piece.branch = {"start_time": new_piece.t,
                                "begin": new_piece.begin,
                                "end_time": None,
                                "end": None,
                                "pieces": []}
            self.branchings.append(new_piece.branch)
            self._counter += 1

    def pieces(self):
        return self._pieces.values()

    def piece(self, key):
        return self._pieces[key]

    def _overlapping_pieces(self, piece):
        return filter(lambda key: self._pieces_overlap(piece, self._pieces[key]),
                      self._pieces.keys())

    def _pieces_overlap(self, piece1, piece2):
        return ((piece2.begin <= piece1.begin <= piece2.end) or
                (piece2.begin <= piece1.end <= piece2.end) or
                (piece1.begin <= piece2.begin <= piece1.end) or
                (piece1.begin <= piece2.end <= piece1.end))

total_size = max([chunk["end"] for chunk in log.chunks])
def time_to_x(t): return t / log.lastchunktime() * options.width
def byte_to_y(byte_pos): return float(byte_pos) / total_size * options.height

class BranchingTracer:
    def __init__(self, chunks):
        self.chunks = chunks

    def trace(self):
        tracker = BranchingTracker()
        for chunk in self.chunks:
            tracker.add(Piece(chunk["t"], chunk["begin"], chunk["end"]))
        #print "\n".join([str(branching) for branching in tracker.branchings]); return
        self.branchings = tracker.branchings

        print '<svg xmlns="http://www.w3.org/2000/svg" version="1.1">'

        print >> sys.stderr, "total_size=%s" % total_size
        self.t = log.lastchunktime()
        self.byte_pos = 0
        while self.byte_pos < total_size:
            print >> sys.stderr, (self.t, self.byte_pos)
            if not self.search_backwards_for_branching():
                break

            self.draw_line(self.t, self.byte_pos,
                           self.branching["start_time"], self.byte_pos)

            self.t = self.branching["start_time"]
            self.byte_pos = self.branching["begin"]
            print >> sys.stderr, (self.t, self.byte_pos)

            self.follow_forwards_until_join()
            self.t = self.branching["end_time"]
            self.byte_pos = self.branching["end"]
            print >> sys.stderr, (self.t, self.byte_pos)
        print '</svg>'

    def search_backwards_for_branching(self):
        branchings_from_here = filter(
            lambda branching: (branching["begin"] == self.byte_pos and
                               branching["start_time"] < self.t),
            self.branchings)
        if len(branchings_from_here) > 0:
            self.branching = max(branchings_from_here, key=lambda branching: branching["start_time"])
            return True
        else:
            return False

    def follow_forwards_until_join(self):
        t1 = self.t
        b1 = self.byte_pos
        for piece in self.branching["pieces"]:
            t2 = piece.t
            b2 = piece.begin
            self.draw_line(t1, b1, t2, b2)
            t1 = t2
            b1 = b2

    def draw_line(self, t1, b1, t2, b2):
        x1 = time_to_x(t1)
        x2 = time_to_x(t2)
        y1 = byte_to_y(b1)
        y2 = byte_to_y(b2)
        print '  <line x1="%f" y1="%f" x2="%f" y2="%f" stroke="black" stroke-width="%f" />' % (
            x1, y1, x2, y2, options.stroke_width)

BranchingTracer(log.chunks).trace()
