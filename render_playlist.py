#!/usr/bin/python

from argparse import ArgumentParser
from render_session import *
from playlist_reader import read_playlist
import os
import pipes

parser = ArgumentParser()
parser.add_argument("playlist")
parser.add_argument("profile", choices=profiles.keys())
parser.add_argument("--visualizer",
                    default="python visual-experiments/waves.py")
parser.add_argument("-f", "--force", action="store_true")
args = parser.parse_args()

playlist = read_playlist(args.playlist)
for item in playlist:
    print "\n\n___ RENDERING %s ___\n" % item["sessiondir"]
    output = "rendered_sessions/%s" % os.path.basename(item["sessiondir"])
    temp_dir = "rendered_sessions/%s" % os.path.basename(item["sessiondir"])
    args_string = " ".join([pipes.quote(arg) for arg in item["args"]])
    SessionRenderer(
        item["sessiondir"],
        args_string,
        args.visualizer,
        output,
        args.profile,
        args.force,
        temp_dir).render()
