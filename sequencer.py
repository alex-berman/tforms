#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
import Queue
import threading
import time
from orchestra import Orchestra, Server
from session import Session
import logger_factory
from logger_factory import logger
import datetime
from shuffler import Shuffler
from playlist_reader import read_playlist

parser = ArgumentParser()
parser.add_argument("sessiondirs", nargs="*")
parser.add_argument("--playlist", type=str)
parser.add_argument("--pause", type=float, default=5.0)
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--preview", type=float)
Server.add_parser_arguments(parser)
logger_factory.add_parser_arguments(parser)
args = parser.parse_args()

logger.setLevel(args.log_level)

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
    orchestra_thread = threading.Thread(name="sequencer.orchestra_thread",
                                        target=orchestra.play_non_realtime,
                                        args=[quit_on_end])
    orchestra_thread.daemon = True
    orchestra_thread.start()

def wait_for_play_completion_or_interruption():
    global orchestra_thread
    while orchestra_thread.is_alive():
        time.sleep(0.1)
    orchestra_thread.join()

if args.playlist and len(args.sessiondirs) > 0:
    raise Exception("cannot specify both playlist and sessiondirs")

if args.playlist:
    playlist = read_playlist(args.playlist)
    for item in playlist:
        item["args"] = orchestra_parser.parse_args(item["args"])
else:
    if len(args.sessiondirs) > 0:
        playlist = [{"sessiondir": sessiondir,
                     "args": orchestra_parser.parse_args([])}
                    for sessiondir in args.sessiondirs]
    else:
        raise Exception("please specify playlist or sessiondirs")

server = Server(args)

def log_open_files():
    global logger
    import subprocess
    n = 0
    p = subprocess.Popen("ls -l /proc/self/fd/", shell=True, stdout=subprocess.PIPE)
    logger.info("output from ls -l /proc/self/fd/:")
    for line in p.stdout:
        line = line.strip()
        logger.info(line)
        n += 1
    logger.info("num open files: %s" % n)

total_duration = 0
for item in playlist:
    item["logfilename"] = "%s/session.log" % item["sessiondir"]
    print "preparing %s" % item["sessiondir"]
    item["tr_log"] = TrLogReader(item["logfilename"]).get_log(reduced_passivity=True)
    item["orchestra"] = Orchestra(server, item["sessiondir"], item["tr_log"], item["args"])
    total_duration += item["orchestra"].estimated_duration

print "-" * 33
print "%-19s%s\n" % ("TOTAL DURATION", datetime.timedelta(seconds=total_duration))

if args.start:
    count = args.start
    print "WARNING: shuffle disabled"
else:
    shuffler = Shuffler(range(len(playlist)))

while True:
    # print "\n\n\nnum threads: %s\n\n" % threading.active_count()
    # print "\nthreads:%s\n" % "\n".join(map(str, threading.enumerate()))
    log_open_files()

    if args.start:
        item = playlist[count % len(playlist)]
        count += 1
    else:
        item = playlist[shuffler.next()]
    print "playing %s" % item["sessiondir"]
    orchestra = item["orchestra"]
    if len(orchestra.chunks) == 0:
        raise Exception("No chunks to play. Unsupported file format?")

    server.set_orchestra(orchestra)

    def stop_orchestra_after_preview():
        time.sleep(args.preview)
        orchestra.stop()
    if args.preview:
        threading.Thread(target=stop_orchestra_after_preview).start()

    play(orchestra, item["args"])
    wait_for_play_completion_or_interruption()

    print "completed playback"

    time.sleep(args.pause)
    orchestra.reset()
