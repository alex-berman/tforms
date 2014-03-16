#!/usr/bin/python

import subprocess
import os
import glob
from argparse import ArgumentParser

RESOLUTION = "-width 720 -height 576"
FPS = 25

# RESOLUTION = "-width 640 -height 360"
# FPS = 30

sessions = [
    ("circle", "*roda_rummet2", "-z 60"),
    ("rect",   "*arvo-part", "-z 30"),
    ("circle", "*utvandrarna-02", "-z 60"),
    ("rect",   "*gulliver", "-z 4"),
    ("circle", "*NIN", "-z 60"),
    ("rect",   "*guthrie", "-z 20"),
    ("circle", "*lord-rings", "-z 15"),
    ("rect",   "*hunger", "-z 60"),
    ("circle", "*miracle", "-z 20"),
    ("rect",   "*roda_rummet2", "-z 60"),
    ("circle", "*potter", "-z 30"),
    ("circle", "*frankenstein", "-z 6"),
    ("rect",   "*potter", "-z 30"),
    ("circle", "*learn*", "-z 2"),
    ("rect",   "*NIN", "-z 60"),
    ("circle", "*gulliver", "-z 4"),
    ("rect",   "*miracle", "-z 20"),
    ("circle", "*adele", "-z 20"),
    ("rect",   "*utvandrarna-02", "-z 60"),
    ("circle", "*guthrie", "-z 20"),
    ("circle", "*hunger", "-z 60"),
    ("rect",   "*frankenstein", "-z 6"),
    ("circle", "*arvo-part", "-z 30"),
    ]

parser = ArgumentParser()
parser.add_argument("--force", "-f", action="store_true")
parser.add_argument("--concat")
args = parser.parse_args()

video_filenames = []
for geometry, session_pattern, render_args in sessions:
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
        cmd = "./revisualize_ancestry.py --geometry=%s %s %s %s --node-style=circle -interpret --sway --sway-magnitude=0.003 --edge-style=line --line-width=1 --node-size-envelope=0.3,25,0.5,0.2 --root-node-size-envelope=0.1,0,1,0.2 --sway-envelope=0,50,0.5,1 --node-size=0.003 --root-node-size=0.005 --prune-out --growth-time-limit=20 -export -export-fps=%s -export-dir=%s" % (geometry, session_dir, render_args, RESOLUTION, FPS, render_dir)
        subprocess.call(cmd, shell=True)

    video_filename = "rendered_ancestry/%s_ancestry_%s.mp4" % (
        os.path.basename(session_dir), geometry)
    print "encoding into %s" % video_filename
    video_filenames.append(video_filename)
    if os.path.exists(video_filename) and not args.force:
        print "video file exists - skipping"
    else:
        cmd = "./encode_exported.py -f -fps %s %s -o %s" % (
            FPS, render_dir, video_filename)
        subprocess.call(cmd, shell=True)

if args.concat:
    cmd = "mencoder -oac pcm -ovc copy -o %s %s" % (
        args.concat, " ".join(video_filenames))
    subprocess.call(cmd, shell=True)
