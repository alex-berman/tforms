#!/usr/bin/python

import subprocess
import os
import glob
from argparse import ArgumentParser

RESOLUTION = "-width 720 -height 576"
FPS = 25

# RESOLUTION = "-width 640 -height 360"
# FPS = 30

sessions_grouped_by_geometry = {
    "circle": [
        # ("*valis", "-z 15", [1, 2]),
        # ("*ulysses", "-z 100", [1]),
        # ("*lord-rings", "-z 10", [1, 2]),
        # ("*miracle", "-z 10", [1, 2]),
        # ("*gulliver", "-z 2", [1, 2]),
        # ("*potter", "-z 5", [2]),
        # ("*frankenstein", "-z 5", [1, 2]),
        # ("*learn*", "", [1, 2]),
        # ("*hunger", "-z 40", [1, 2]),
        # ("*chopin", "-z 20", [1, 2]),
        # ("*adele", "-z 20", [1]),

        # ("*guthrie", "-z 20", [1]),
        ("*hunger", "-z 40", [1]),
        # ("*arvo-part", "-z 30", [1]),
        # ("*utvandrarna-02", "-z 60", [1]),
        # ("*roda_rummet2", "-z 60", [1]),
        ],

    "rect": [
        ("*roda_rummet2", "-z 60", [1]),
        # ("*utvandrarna-02", "-z 60", [1]),
        # ("*NIN", "-z 60", [1]),
        ],
    }

parser = ArgumentParser()
parser.add_argument("--force", "-f", action="store_true")
args = parser.parse_args()

for geometry, sessions in sessions_grouped_by_geometry.iteritems():
    for (session_pattern, render_args, timefactors) in sessions:
        matches = glob.glob("sessions/%s" % session_pattern)
        if len(matches) == 1:
            session_dir = matches[0]
        elif len(matches) == 0:
            raise Exception("no sessions matching %s" % session_pattern)
        else:
            raise Exception("more than one session matching %s" % session_pattern)

        render_dir = "%s/rendered_Ancestry_%s" % (session_dir, geometry)
        print "rendering into %s" % render_dir
        if os.path.exists(render_dir) and not args.force:
            print "rendering directory exists - skipping"
        else:
            cmd = "./revisualize_ancestry.py --geometry=%s %s %s %s --node-style=circle -interpret --sway --sway-magnitude=0.003 --edge-style=line --line-width=1 --node-size-envelope=0.3,25,0.5,0.2 --root-node-size-envelope=0.1,0,1,0.2 --sway-envelope=0,50,0.5,1 --node-size=0.003 --root-node-size=0.005 --prune-out -export -export-fps=%s -export-dir=%s" % (geometry, session_dir, render_args, RESOLUTION, FPS, render_dir)
            subprocess.call(cmd, shell=True)

        for timefactor in timefactors:
            video_filename = "rendered_ancestry/%s_ancestry_z%s_%s.mp4" % (
                os.path.basename(session_dir), timefactor, geometry)
            print "encoding into %s" % video_filename
            if os.path.exists(video_filename) and not args.force:
                print "video file exists - skipping"
            else:
                cmd = "./encode_exported.py -f -fps %s %s -o %s" % (
                    FPS * timefactor, render_dir, video_filename)
                subprocess.call(cmd, shell=True)
