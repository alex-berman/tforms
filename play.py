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
Orchestra.add_parser_arguments(parser)
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

orchestra = Orchestra(sessiondir, tr_log, options)

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

if options.realtime:
    run_realtime()
else:
    run_offline()

orchestra.shutdown()
