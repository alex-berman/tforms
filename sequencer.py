#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
import Queue
import threading
import time
from orchestra import Orchestra, Server
from session import Session
from logger import logger

parser = ArgumentParser()
parser.add_argument("sessiondirs", nargs="+")
parser.add_argument("--pause", type=float, default=5.0)
Server.add_parser_arguments(parser)
Orchestra.add_parser_arguments(parser)
options = parser.parse_args()

assert not options.realtime

def get_chunk_from_queue():
    while True:
        try:
            # having a timeout allows ctrl-c to interrupt
            return tr_log.chunks_queue.get(True, timeout=10)
        except Queue.Empty:
            pass

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
    while orchestra_thread.is_alive():
        time.sleep(0.1)

server = Server(options)
count = 0
while True:
    sessiondir = options.sessiondirs[count % len(options.sessiondirs)]
    logfilename = "%s/session.log" % sessiondir
    print "playing %s" % sessiondir

    tr_log = TrLogReader(logfilename, options.torrentname,
                         realtime=options.realtime,
                         pretend_sequential=options.pretend_sequential).get_log()

    orchestra = Orchestra(sessiondir, tr_log, options)
    server.set_orchestra(orchestra)

    if not options.realtime and len(orchestra.chunks) == 0:
        raise Exception("No chunks to play. Unsupported file format?")

    play()
    wait_for_play_completion_or_interruption()

    print "completed playback"

    time.sleep(options.pause)
    orchestra.reset()
    count += 1
