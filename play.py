#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
import Queue
import threading
import time
from orchestra import Orchestra
from session import Session
import subprocess
from logger import logger

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--rt", action="store_true", dest="realtime")
parser.add_argument("-t", "--torrent", dest="torrentname", default="")
parser.add_argument("-z", "--timefactor", dest="timefactor", type=float, default=1)
parser.add_argument("--start", dest="start_time", type=float, default=0)
parser.add_argument("-q", "--quiet", action="store_true", dest="quiet")
parser.add_argument("--pretend-sequential", action="store_true", dest="pretend_sequential")
parser.add_argument("--gui", action="store_true", dest="gui_enabled")
parser.add_argument("--predecode", action="store_true", dest="predecode", default=True)
parser.add_argument("--download-location", dest="download_location", default="../../Downloads")
parser.add_argument("--visualize", dest="visualizer_enabled", action="store_true")
parser.add_argument("--visualizer", dest="visualizer")
parser.add_argument("--fast-forward", action="store_true", dest="ff")
parser.add_argument("--fast-forward-to-start", action="store_true", dest="ff_to_start")
parser.add_argument("--quit-at-end", action="store_true", dest="quit_at_end")
parser.add_argument("--loop", dest="loop", action="store_true")
parser.add_argument("--osc-log", dest="osc_log")
parser.add_argument("--max-passivity", dest="max_passivity", type=float)
parser.add_argument("--max-pause-within-segment", dest="max_pause_within_segment", type=float)
parser.add_argument("--looped-duration", dest="looped_duration", type=float)
parser.add_argument("-o", "--output", dest="output", type=str, default=Orchestra.SSR)
options = parser.parse_args()

if options.realtime:
    if options.max_passivity:
        raise Exception("cannot enforce max passivity in real time")
    session = Session(realtime=True)
    sessiondir = session.dir
    logfile = session.get_log_reader()
    session.start()
else:
    sessiondir = options.sessiondir
    logfilename = "%s/session.log" % sessiondir

print "session: %s" % sessiondir

tr_log = TrLogReader(logfilename, options.torrentname,
                     realtime=options.realtime,
                     pretend_sequential=options.pretend_sequential).get_log()

if options.predecode:
    from predecode import Predecoder
    predecoder = Predecoder(tr_log, options.download_location, Orchestra.SAMPLE_RATE)
    predecoder.decode()

orchestra = Orchestra(sessiondir,
                      tr_log,
                      realtime=options.realtime,
                      timefactor=options.timefactor,
                      start_time=options.start_time,
                      ff_to_start=options.ff_to_start,
                      quiet=options.quiet,
                      predecoded=options.predecode,
                      file_location=options.download_location,
                      visualizer_enabled=(options.visualizer_enabled or options.visualizer),
                      loop=options.loop,
                      osc_log=options.osc_log,
                      max_passivity=options.max_passivity,
                      max_pause_within_segment=options.max_pause_within_segment,
                      looped_duration=options.looped_duration,
                      output=options.output)

if not options.realtime and len(orchestra.chunks) == 0:
    raise Exception("No chunks to play. Unsupported file format?")

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

def run_offline():
    if options.gui_enabled:
        from gui import GUI
        gui = GUI(orchestra)
        gui.main_loop()
    else:
        play()
        wait_for_play_completion_or_interruption()

def play():
    global orchestra_thread
    quit_on_end = False
    orchestra.fast_forwarding = options.ff or options.ff_to_start
    orchestra_thread = threading.Thread(target=orchestra.play_non_realtime,
                                        args=[quit_on_end])
    orchestra_thread.daemon = True
    orchestra_thread.start()

def wait_for_play_completion_or_interruption():
    global orchestra_thread
    while orchestra_thread.is_alive() or not options.quit_at_end:
        time.sleep(0.1)

if options.visualizer:
    visualizer_process = subprocess.Popen(options.visualizer, shell=True, stdin=None)

if options.realtime:
    run_realtime()
else:
    run_offline()

orchestra.shutdown()
