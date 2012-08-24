#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
import subprocess
import matplotlib
import colors
sys.path.insert(0, "visual-experiments")
from gatherer import Gatherer
from visualizer import Chunk

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-width", type=float, default=500)
parser.add_argument("-height", type=float, default=500)
parser.add_argument("-stroke_width", type=float, default=5)
parser.add_argument("-resolution", type=float, help="Horizontal dots per second", default=100.0)
options = parser.parse_args()

logfilename = "%s/session.log" % options.sessiondir
log = TrLogReader(logfilename, options.torrentname, options.filenum).get_log()
print >> sys.stderr, "found %d chunks" % len(log.chunks)

total_size = max([chunk["end"] for chunk in log.chunks])

print '<svg xmlns="http://www.w3.org/2000/svg" version="1.1">'

def time_to_x(t): return t / log.lastchunktime() * options.width
def byte_to_y(byte_pos): return float(byte_pos) / total_size * options.height

class Piece:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

peer_colors = colors.colors(len(log.peers))
peers = {}

def render_slice(t):
    x1 = x2 = time_to_x(t)
    for gatherer, color in zip(peers.values(), peer_colors):
        for piece in gatherer.pieces():
            y1 = byte_to_y(piece.begin)
            y2 = byte_to_y(piece.end)
            (r,g,b,a) = color
            print '  <line x1="%f" y1="%f" x2="%f" y2="%f" stroke="rgb(%i,%i,%i)" stroke-width="%f" />' % (
                x1, y1, x2, y2, r*255, g*255, b*255, options.stroke_width)

previous_slice_time = None
seconds_per_slice = 1.0 / options.resolution
for chunk in log.chunks:
    peer_id = log.peeraddr_to_id[chunk["peeraddr"]]
    try:
        peer = peers[peer_id]
    except KeyError:
        peer = peers[peer_id] = Gatherer()
    peer.add(Piece(chunk["begin"], chunk["end"]))
    if previous_slice_time is None or (chunk["t"] - previous_slice_time) >= seconds_per_slice:
        render_slice(chunk["t"])
        previous_slice_time = chunk["t"]

print '</svg>'
