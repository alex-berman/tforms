#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
from ancestry_tracker import *
import sys

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

tracker = AncestryTracker()
for chunk in log.chunks:
    tracker.add(Piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"]))

total_size = max([chunk["end"] for chunk in log.chunks])

def time_to_x(t): return t / log.lastchunktime() * options.width
def byte_to_y(byte_pos): return float(byte_pos) / total_size * options.height

def draw_line(t1, b1, t2, b2):
    x1 = time_to_x(t1)
    x2 = time_to_x(t2)
    y1 = byte_to_y(b1)
    y2 = byte_to_y(b2)
    print '  <line x1="%f" y1="%f" x2="%f" y2="%f" stroke="black" stroke-width="%f" />' % (
        x1, y1, x2, y2, options.stroke_width)

def follow_piece(piece):
    for parent in piece.parents.values():
        draw_line(piece.t, (piece.begin + piece.end) / 2,
                  parent.t, (parent.begin + parent.end) / 2)
        follow_piece(parent)

print '<svg xmlns="http://www.w3.org/2000/svg" version="1.1">'
print '<rect width="%f" height="%f" fill="white" />' % (options.width, options.height)
sys.setrecursionlimit(len(log.chunks))
follow_piece(tracker.last_piece())
print '</svg>'
