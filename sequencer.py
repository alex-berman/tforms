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
import datetime

parser = ArgumentParser()
parser.add_argument("sessiondirs", nargs="*")
parser.add_argument("--playlist", type=str)
parser.add_argument("--pause", type=float, default=5.0)
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--get-duration", action="store_true")
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

def play(orchestra, args):
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
            item["sessiondir"] = matches[0]
        elif len(matches) == 0:
            raise Exception("no sessions matching %s" % item["session"])
        else:
            raise Exception("more than one session matching %s" % item["session"])
        item["args"] = orchestra_parser.parse_args(item["args"])

else:
    if len(args.sessiondirs) > 0:
        playlist = [{"sessiondir": sessiondir,
                     "args": orchestra_parser.parse_args([])}
                    for sessiondir in args.sessiondirs]
    else:
        raise Exception("please specify playlist or sessiondirs")

for item in playlist:
    item["logfilename"] = "%s/session.log" % item["sessiondir"]

if args.get_duration:
    total_duration = 0
    for item in playlist:
        tr_log = TrLogReader(item["logfilename"]).get_log(reduced_passivity=True)
        duration = Orchestra.estimate_duration(tr_log, item["args"])
        print "%-50s%s" % (item["sessiondir"], datetime.timedelta(seconds=duration))
        total_duration += duration
    print "-" * 64
    print "%-50s%s" % ("TOTAL DURATION", datetime.timedelta(seconds=total_duration))

else:
    server = Server(args)
    count = args.start

    while True:
        item = playlist[count % len(playlist)]
        if not "orchestra" in item:
            print "preparing %s" % item["sessiondir"]
            tr_log = TrLogReader(item["logfilename"]).get_log(reduced_passivity=True)
            item["orchestra"] = Orchestra(server, item["sessiondir"], tr_log, item["args"])

        print "playing %s" % item["sessiondir"]
        orchestra = item["orchestra"]
        if len(orchestra.chunks) == 0:
            raise Exception("No chunks to play. Unsupported file format?")

        # <TEMP> (quickly skip from item to item, e.g. to provoke memory leak problem)
        # def stop_orchestra_within_short():
        #     time.sleep(2.0)
        #     orchestra.stop()
        # threading.Thread(target=stop_orchestra_within_short).start()
        # </TEMP>

        server.set_orchestra(orchestra)
        play(orchestra, item["args"])
        wait_for_play_completion_or_interruption()

        print "completed playback"

        time.sleep(args.pause)
        orchestra.reset()
        count += 1
