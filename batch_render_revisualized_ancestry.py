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
        ("*roda_rummet2", "-z 60"),
        ("*utvandrarna-02", "-z 60"),
        ("*NIN", "-z 60"),

        ("*valis", "-z 25"),
        ("*lord-rings", "-z 15"),
        ("*miracle", "-z 20"),
        ("*gulliver", "-z 4"),
        ("*potter", "-z 30"),
        ("*frankenstein", "-z 6"),
        ("*learn*", "-z 2"),
        ("*chopin", "-z 20"),
        ("*adele", "-z 20"),

        ("*guthrie", "-z 20"),
        ("*hunger", "-z 60"),
        ("*arvo-part", "-z 30"),
        ],

    "rect": [
        ("*roda_rummet2", "-z 60"),
        ("*utvandrarna-02", "-z 60"),
        ("*NIN", "-z 60"),

        ("*miracle", "-z 20"),
        ("*gulliver", "-z 4"),
        ("*potter", "-z 30"),
        ("*frankenstein", "-z 6"),
        ("*chopin", "-z 20"),

        ("*guthrie", "-z 20"),
        ("*hunger", "-z 60"),
        ("*arvo-part", "-z 30"),
        ],
    }

parser = ArgumentParser()
parser.add_argument("--force", "-f", action="store_true")
args = parser.parse_args()

for geometry, sessions in sessions_grouped_by_geometry.iteritems():
    for (session_pattern, render_args) in sessions:
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

        video_filename = "rendered_ancestry/%s_ancestry_%s.mp4" % (
            os.path.basename(session_dir), geometry)
        print "encoding into %s" % video_filename
        if os.path.exists(video_filename) and not args.force:
            print "video file exists - skipping"
        else:
            cmd = "./encode_exported.py -f -fps %s %s -o %s" % (
                FPS, render_dir, video_filename)
            subprocess.call(cmd, shell=True)
