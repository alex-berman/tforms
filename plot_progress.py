#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
import subprocess
import matplotlib
import colors

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-width", type=float, default=500)
parser.add_argument("-height", type=float, default=500)
parser.add_argument("-stroke_width", type=float, default=5)
options = parser.parse_args()

logfilename = "%s/session.log" % options.sessiondir
log = TrLogReader(logfilename, options.torrentname, options.filenum).get_log()
print >> sys.stderr, "found %d chunks" % len(log.chunks)

total_size = max([chunk["end"] for chunk in log.chunks])

print '<svg xmlns="http://www.w3.org/2000/svg" version="1.1">'

def time_to_x(t): return t / log.lastchunktime() * options.width
def byte_to_y(byte_pos): return float(byte_pos) / total_size * options.height

peer_colors = colors.colors(len(log.peers))

files = {}
for chunk in log.chunks:
    x1 = x2 = time_to_x(chunk["t"])
    y1 = byte_to_y(chunk["begin"])
    y2 = byte_to_y(chunk["end"])
    (r,g,b,a) = peer_colors[log.peeraddr_to_id[chunk["peeraddr"]]]
    print '  <line x1="%f" y1="%f" x2="%f" y2="%f" stroke="rgb(%i,%i,%i)" stroke-width="%f" />' % (
        x1, y1, x2, y2, r*255, g*255, b*255, options.stroke_width)

print '</svg>'
