#!/usr/bin/python

from tr_log_reader import *
from optparse import OptionParser
import subprocess

parser = OptionParser()
parser.add_option("-s", "--sessiondir", dest="sessiondir")
parser.add_option("-t", "--torrent", dest="torrentname", default="")
parser.add_option("-n", "--filenum", dest="filenum", type="int")
parser.add_option("--splitfiles", dest="splitfiles", action="store_true")
parser.add_option("--splitpeers", dest="splitpeers", action="store_true")
parser.add_option("--datatitles", dest="datatitles", action="store_true")
parser.add_option("--png", dest="save_png", action="store_true")
parser.add_option("--plot", dest="plot",
                  choices=["chunks", "speed"],
                  default="chunks")
(options, args) = parser.parse_args()

logfilename = "%s/session.log" % options.sessiondir
log = TrLogReader(logfilename, options.torrentname, options.filenum).get_log()
print >> sys.stderr, "found %d chunks" % len(log.chunks)

def _data_title(title):
    if options.datatitles:
        return 'title "%s"' % title
    else:
        return 'notitle'

def write_chunks_data(log, f=sys.stdout, filenum=None, peer_num=None):
    chunks_to_plot = log.chunks
    if filenum:
        chunks_to_plot = filter(lambda x: x["filenum"] == filenum,
                                chunks_to_plot)
    if peer_num:
        peeraddr = log.peers[peer_num]
        chunks_to_plot = filter(lambda x: x["peeraddr"] == peeraddr,
                                chunks_to_plot)
    for chunk in chunks_to_plot:
        write_chunk_data(f, chunk)

def write_chunk_data(f, chunk):
    f.write("%f %d %d\n" % (chunk["t"], chunk["begin"], chunk["end"]))

def write_speed_data(log, f, peer_num):
    chunks_to_plot = log.chunks
    peeraddr = log.peers[peer_num]
    chunks_to_plot = filter(lambda x: x["peeraddr"] == peeraddr,
                            chunks_to_plot)
    previous_chunk_time = None
    for chunk in chunks_to_plot:
        if previous_chunk_time:
            download_time = chunk["t"] - previous_chunk_time
            if download_time > 0:
                speed = (chunk["end"] - chunk["begin"]) / download_time
                f.write("%f %f\n" % (chunk["t"], speed))
        previous_chunk_time = chunk["t"]

plotcommands = []

if options.plot == "chunks":
    for i in range(len(log.files) - 1):
        byte_pos = log.files[i]["offset"] + log.files[i]["length"]
        plotcommands.append('%d with lines lc rgbcolor "#e0e0e0" notitle' % byte_pos)

    if options.splitpeers:
        for i in range(len(log.peers)):
            plotfilename = "%s/plotdata%d.txt" % (options.sessiondir, i)
            plotcommands.append('"%s" using ($1):($2):(0):($3-$2) with vectors nohead %s' %
                                (plotfilename, _data_title("Peer %d" % (i+1))))
            with open(plotfilename, "w") as f:
                write_chunks_data(log, f, peer_num=i)
    elif options.splitfiles:
        for i in range(len(log.files)):
            plotfilename = "%s/plotdata%d.txt" % (options.sessiondir, i)
            plotcommands.append('"%s" using ($1):($2):(0):($3-$2) with vectors nohead %s' % \
                                    (plotfilename, _data_title("File %d" % (i+1))))
            with open(plotfilename, "w") as f:
                write_chunks_data(log, f, filenum=i)
    else:
        raise Exception("must split by files or peers")

elif options.plot == "speed":
    if options.splitpeers:
        for i in range(len(log.peers)):
            plotfilename = "%s/plotdata%d.txt" % (options.sessiondir, i)
            plotcommands.append('"%s" with points %s' %
                                (plotfilename, _data_title("Peer %d" % (i+1))))
            with open(plotfilename, "w") as f:
                write_speed_data(log, f, peer_num=i)
    else:
        raise Exception("not supported")

plotcommand_filename = "%s/plotcommand.txt" % options.sessiondir
with open(plotcommand_filename, "w") as f:
    if options.save_png:
        png_filename = '%s/plot.png' % options.sessiondir 
        f.write('set term png nocrop enhanced font "/usr/share/fonts/truetype/ttf-liberation/LiberationSans-Regular.ttf" 10 size 640,480\n')
        f.write('set output "%s"\n' % png_filename)
    f.write('unset ytics\n')
    f.write("plot %s\n" % ", \\\n".join(plotcommands))

if options.save_png:
    subprocess.call('gnuplot "%s"' % plotcommand_filename,
                    shell=True)
    print "saved plot to %s" % png_filename
