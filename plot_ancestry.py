#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
from ancestry_plotter import AncestrySvgPlotter
import sys

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("--file", dest="selected_files", type=int, nargs="+")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-width", type=int)
parser.add_argument("-height", type=int)
parser.add_argument("-stroke-color", type=str, default="black")
parser.add_argument("-stroke-width", type=float, default=1)
parser.add_argument("-f", "--force", action="store_true")
parser.add_argument("-o", dest="output_filename")
AncestrySvgPlotter.add_parser_arguments(parser)
args = parser.parse_args()

output_filename = args.output_filename
if not output_filename:
    output_filename = "%s/ancestry.svg" % args.sessiondir

if os.path.exists(output_filename) and not args.force:
    print >>sys.stderr, "%s already exists. Skipping." % output_filename
    sys.exit(-1)

logfilename = "%s/session.log" % args.sessiondir
log = TrLogReader(logfilename, args.torrentname, args.filenum).get_log()
if args.selected_files:
    log.select_files(args.selected_files)
print >> sys.stderr, "found %d chunks" % len(log.chunks)
log.ignore_non_downloaded_files()

output = open(output_filename, "w")
plotter = AncestrySvgPlotter(log.total_file_size(), log.lastchunktime(), args)
plotter.set_size(args.width, args.height)
for chunk in log.chunks:
    plotter.add_piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"])
plotter.plot(output)

output.close()
print "plot: %s" % output_filename
