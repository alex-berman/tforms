#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
import Queue
import threading
import time
from orchestra import Orchestra, Server
from session import Session
from logger import logger
import glob

parser = ArgumentParser()
parser.add_argument("sessiondirs", nargs="*")
parser.add_argument("--playlist", type=str)
parser.add_argument("--pause", type=float, default=5.0)
parser.add_argument("--start", type=int, default=0)
Server.add_parser_arguments(parser)
args = parser.parse_args()

orchestra_parser = ArgumentParser()
Orchestra.add_parser_arguments(orchestra_parser)

def get_chunk_from_queue():
    while True:
        try:
            # having a timeout allows ctrl-c to interrupt
            return tr_log.chunks_queue.get(True, timeout=10)
        except Queue.Empty:
            pass

def play(args):
    global orchestra_thread
    quit_on_end = False
    orchestra.fast_forwarding = args.ff or args.ff_to_start
    orchestra_thread = threading.Thread(target=orchestra.play_non_realtime,
                                        args=[quit_on_end])
    orchestra_thread.daemon = True
    orchestra_thread.start()

def wait_for_play_completion_or_interruption():
    global orchestra_thread
    while orchestra_thread.is_alive():
        time.sleep(0.1)

if args.playlist and len(args.sessiondirs) > 0:
    raise Exception("cannot specify both playlist and sessiondirs")

if args.playlist:
    playlist_module = __import__(args.playlist)
    playlist = playlist_module.playlist
    for item in playlist:
        matches = glob.glob(item["session"])
        if len(matches) == 1:
            item["session"] = matches[0]
        elif len(matches) == 0:
            raise Exception("no sessions matching %s" % item["session"])
        else:
            raise Exception("more than one session matching %s" % item["session"])
        item["args"] = orchestra_parser.parse_args(item["args"].split())

else:
    if len(args.sessiondirs) > 0:
        playlist = [{"session": sessiondir,
                     "args": orchestra_parser.parse_args([])}
                    for sessiondir in args.sessiondirs]
    else:
        raise Exception("please specify playlist or sessiondirs")

server = Server(args)
count = args.start

while True:
    playlist_item = playlist[count % len(playlist)]
    sessiondir = playlist_item["session"]
    logfilename = "%s/session.log" % sessiondir
    print "playing %s" % sessiondir

    tr_log = TrLogReader(logfilename).get_log(reduced_passivity=True)
    orchestra = Orchestra(server, sessiondir, tr_log, playlist_item["args"])

    if len(orchestra.chunks) == 0:
        raise Exception("No chunks to play. Unsupported file format?")

    play(playlist_item["args"])
    wait_for_play_completion_or_interruption()

    print "completed playback"

    time.sleep(args.pause)
    orchestra.reset()
    count += 1
