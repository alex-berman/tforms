#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
import ancestry_plotter
import sys
from interpret import Interpreter

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
parser.add_argument("--file", dest="selected_files", type=int, nargs="+")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-n", "--filenum", dest="filenum", type=int)
parser.add_argument("-f", "--force", action="store_true")
parser.add_argument("-o", dest="output_filename")
parser.add_argument("-interpret", action="store_true")
ancestry_plotter.AncestryPlotter.add_parser_arguments(parser)
args = parser.parse_args()

output_filename = args.output_filename
if not output_filename:
    output_filename = "%s/ancestry.%s" % (args.sessiondir, args.output_type)

if os.path.exists(output_filename) and not args.force:
    print >>sys.stderr, "%s already exists. Skipping." % output_filename
    sys.exit(-1)

logfilename = "%s/session.log" % args.sessiondir
log = TrLogReader(logfilename, args.torrentname, args.filenum).get_log()
if args.selected_files:
    log.select_files(args.selected_files)
print >> sys.stderr, "found %d chunks" % len(log.chunks)

if args.interpret:
    pieces = Interpreter().interpret(log.chunks)
else:
    pieces = log.chunks

output = open(output_filename, "w")
plotter_class = ancestry_plotter.OUTPUT_TYPES[args.output_type]
plotter = plotter_class(log.total_file_size(), log.lastchunktime(), args)
plotter.set_size(args.width, args.height)
for chunk in pieces:
    plotter.add_piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"])
plotter.plot(output)

output.close()

if args.output_type == "dot":
    print "plot with:"
    print "neato %s -Tps -o%s/ancestry_neato.ps" % (output_filename, args.sessiondir)
else:
    print "plot: %s" % output_filename
