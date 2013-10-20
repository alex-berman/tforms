#!/usr/bin/python

from argparse import ArgumentParser
from render_session import SessionRenderer
from playlist_reader import read_playlist
import os
import pipes

parser = ArgumentParser()
parser.add_argument("playlist")
parser.add_argument("--visualizer",
                    # default="python visual-experiments/waves.py -width 720 -height 576")
                    default="python visual-experiments/waves_and_heat_map.py -width 720 -height 576 -left 0 -top 0 --map-margin=0.7,0,0,0 --waves-margin=0,0,0.3,0 --text-renderer=ftgl --font=fonts/simplex_.ttf --peer-info")
args = parser.parse_args()

playlist = read_playlist(args.playlist)
for item in playlist:
    print "\n\n___ RENDERING %s ___\n" % item["sessiondir"]
    output = "rendered_sessions/%s.mp4" % os.path.basename(item["sessiondir"])
    temp_dir = "rendered_sessions/%s" % os.path.basename(item["sessiondir"])
    args_string = " ".join([pipes.quote(arg) for arg in item["args"]])
    SessionRenderer(
        item["sessiondir"],
        args_string,
        args.visualizer,
        output,
        temp_dir).render()
