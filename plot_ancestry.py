#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
from ancestry_plotter import AncestryPlotter
import sys

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-width", type=int, default=500)
parser.add_argument("-height", type=int, default=500)
parser.add_argument("-stroke_width", type=float, default=1)
parser.add_argument("-f", "--force", action="store_true")
parser.add_argument("-o", dest="output_filename")
parser.add_argument("--edge-style",
                    choices=[AncestryPlotter.LINE, AncestryPlotter.CURVE],
                    default=AncestryPlotter.CURVE)
parser.add_argument("--geometry",
                    choices=[AncestryPlotter.RECT, AncestryPlotter.CIRCLE],
                    default=AncestryPlotter.RECT)
options = parser.parse_args()

output_filename = options.output_filename
if not output_filename:
    output_filename = "%s/ancestry.svg" % options.sessiondir

if os.path.exists(output_filename) and not options.force:
    print >>sys.stderr, "%s already exists. Skipping." % output_filename
    sys.exit(-1)

logfilename = "%s/session.log" % options.sessiondir
log = TrLogReader(logfilename, options.torrentname, options.filenum).get_log()
print >> sys.stderr, "found %d chunks" % len(log.chunks)
log.ignore_non_downloaded_files()

output = open(output_filename, "w")
AncestryPlotter(log.chunks, options).plot(output)
output.close()
print "plot: %s" % output_filename
