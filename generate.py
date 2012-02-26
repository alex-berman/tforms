#!/usr/bin/python

import logging
from tr_log_reader import *
from optparse import OptionParser
from orchestra import Orchestra
from audio_buffer import *

logging.basicConfig(filename="generate.log", 
                    level=logging.DEBUG, 
                    filemode="w")
logger = logging.getLogger("generate")

parser = OptionParser()
parser.add_option("-s", "--sessiondir", dest="sessiondir")
parser.add_option("-o", "--output", dest="output_filename", default=None)
parser.add_option("-t", "--torrent", dest="torrentname", default="")
parser.add_option("--predecode", action="store_true", dest="predecode", default=True)
parser.add_option("--download-location", dest="download_location", default="../../Downloads")
parser.add_option("--sm", "--speed-metaphor", dest="speed_metaphor",
                  choices=[Orchestra.STRETCH,
                           Orchestra.PITCH],
                  default=Orchestra.STRETCH)
parser.add_option("--from", dest="from_time", type=float)
parser.add_option("--to", dest="to_time", type=float)
parser.add_option("--content", dest="content",
                  choices=[Orchestra.TRANSFERRED,
                           Orchestra.NOISE],
                  default=Orchestra.TRANSFERRED)
(options, args) = parser.parse_args()

sessiondir = options.sessiondir
logfilename = "%s/session.log" % sessiondir

tr_log = TrLogReader(logfilename, options.torrentname,
                     logger,
                     realtime=False).get_log()

if options.predecode:
    from predecode import Predecoder
    predecoder = Predecoder(tr_log, options.download_location, Orchestra.SAMPLE_RATE)
    predecoder.decode()

orchestra = Orchestra(sessiondir,
                      logger,
                      tr_log,
                      realtime=False,
                      predecoded=options.predecode,
                      file_location=options.download_location,
                      speed_metaphor=options.speed_metaphor,
                      content=options.content)

print "generating..."
output_buffer = orchestra.render(options.from_time, options.to_time)
print "ok"

if options.output_filename:
    output_filename = options.output_filename
else:
    output_filename = "%s/output.wav" % sessiondir

writer = AudioWriter(output_buffer.getframes(), output_filename,
                     nchannels=2, samplerate=Orchestra.SAMPLE_RATE, samplesize=2)
writer.write()
