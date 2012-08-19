#!/usr/bin/python

from tr_log_reader import TrLogReader
from optparse import OptionParser
import logging
import Queue
import threading
import time
from orchestra import Orchestra
from session import Session
import subprocess

logging.basicConfig(filename="play.log", 
                    level=logging.DEBUG, 
                    filemode="w")
logger = logging.getLogger("play")

parser = OptionParser()
parser.add_option("--rt", action="store_true", dest="realtime")
parser.add_option("-s", "--sessiondir", dest="sessiondir")
parser.add_option("-t", "--torrent", dest="torrentname", default="")
parser.add_option("-z", "--timefactor", dest="timefactor", type="float", default=1)
parser.add_option("--start", dest="start_time", type="float", default=0)
parser.add_option("-q", "--quiet", action="store_true", dest="quiet")
parser.add_option("--pretend-sequential", action="store_true", dest="pretend_sequential")
parser.add_option("--gui", action="store_true", dest="gui_enabled")
parser.add_option("--predecode", action="store_true", dest="predecode", default=True)
parser.add_option("--download-location", dest="download_location", default="../../Downloads")
parser.add_option("--visualize", dest="visualizer_enabled", action="store_true")
parser.add_option("--visualizer", dest="visualizer")
parser.add_option("--loop", dest="loop", action="store_true")
parser.add_option("--osc-log", dest="osc_log")
(options, args) = parser.parse_args()

if options.realtime:
    session = Session(realtime=True)
    sessiondir = session.dir
    logfile = session.get_log_reader()
    session.start()
else:
    sessiondir = options.sessiondir
    logfilename = "%s/session.log" % sessiondir

print "session: %s" % sessiondir

tr_log = TrLogReader(logfilename, options.torrentname,
                     logger,
                     realtime=options.realtime,
                     pretend_sequential=options.pretend_sequential).get_log()

if options.predecode:
    from predecode import Predecoder
    predecoder = Predecoder(tr_log, options.download_location, logger, Orchestra.SAMPLE_RATE)
    predecoder.decode()

orchestra = Orchestra(sessiondir,
                      logger,
                      tr_log,
                      realtime=options.realtime,
                      timefactor=options.timefactor,
                      start_time=options.start_time,
                      quiet=options.quiet,
                      predecoded=options.predecode,
                      file_location=options.download_location,
                      visualizer_enabled=(options.visualizer_enabled or options.visualizer),
                      loop=options.loop,
                      osc_log=options.osc_log)

def process_chunks_from_queue():
    while True:
        logger.debug("waiting for chunk")
        chunk = get_chunk_from_queue()
        if chunk == TrLogReader.NO_MORE_CHUNKS:
            logger.debug("no more chunks")
            return
        orchestra.handle_chunk(chunk)

def get_chunk_from_queue():
    while True:
        try:
            # having a timeout allows ctrl-c to interrupt
            return tr_log.chunks_queue.get(True, timeout=10)
        except Queue.Empty:
            pass

def run_realtime():
    log_reader_thread = threading.Thread(target=tr_log.process_log)
    log_reader_thread.daemon = True
    log_reader_thread.start()
    process_chunks_from_queue()

def play():
    global orchestra_thread
    orchestra_thread = threading.Thread(target=orchestra.play_non_realtime)
    orchestra_thread.daemon = True
    orchestra_thread.start()

def wait_for_play_completion_or_interruption():
    global orchestra_thread
    while orchestra_thread.is_alive():
        time.sleep(0.1)

if options.visualizer:
    visualizer_process = subprocess.Popen(options.visualizer, shell=True, stdin=None)

if options.realtime:
    run_realtime()
else:
    if options.gui_enabled:
        from gui import GUI
        gui = GUI(orchestra)
        gui.main_loop()
    else:
        play()
        wait_for_play_completion_or_interruption()

orchestra.shutdown()
