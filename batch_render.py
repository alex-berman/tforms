#!/usr/bin/python

import subprocess
import os
import glob

# RESOLUTION = "-width 720 -height 576"
# FPS = 25

RESOLUTION = "-width 640 -height 360"
FPS = 30

sessions = [
    ("*valis", "-z 15", [1, 2]),
    ("*ulysses", "-z 100", [1]),
    ("*lord-rings", "-z 10", [1, 2]),
    ("*miracle", "-z 10", [1, 2]),
    ("*gulliver", "-z 2", [1, 2]),
    ("*potter", "-z 5", [2]),
    ("*frankenstein", "-z 5", [1, 2]),
    ("*learn*", "", [1, 2]),
    ("*hunger", "-z 40", [1, 2]),
    ("*chopin", "-z 20", [1, 2]),
    ("*adele", "-z 20", [1]),
    ]

for (session_pattern, args, timefactors) in sessions:
    matches = glob.glob("sessions/%s" % session_pattern)
    if len(matches) == 1:
        session_dir = matches[0]
    elif len(matches) == 0:
        raise Exception("no sessions matching %s" % session_pattern)
    else:
        raise Exception("more than one session matching %s" % session_pattern)

    render_dir = "%s/rendered_Ancestry" % session_dir
    print "rendering into %s" % render_dir
    if os.path.exists(render_dir):
        print "rendering directory exists - skipping"
    else:
        cmd = "./revisualize_ancestry.py --geometry=circle %s %s %s --node-style=circle --unfold=forward -interpret --sway --sway-magnitude=0.003 --edge-style=line --line-width=1 --node-size-envelope=0.3,25,0.5,0.2 --root-node-size-envelope=0.1,0,1,0.2 --sway-envelope=0,50,0.5,1 --node-size=0.003 -export -export-fps=%s" % (session_dir, args, RESOLUTION, FPS)
        subprocess.call(cmd, shell=True)

    for timefactor in timefactors:
        video_filename = "rendered_ancestry/%s_ancestry_z%s.mp4" % (
            os.path.basename(session_dir), timefactor)
        print "encoding into %s" % video_filename
        if os.path.exists(video_filename):
            print "video file exists - skipping"
        else:
            # cmd = "./encode_exported.py -f -fps %s -fade-out 3.0 %s Ancestry -o %s" % (
            #     FPS * timefactor, session_dir, video_filename)
            cmd = "./encode_exported.py -f -fps %s %s Ancestry -o %s" % (
                FPS * timefactor, session_dir, video_filename)
            subprocess.call(cmd, shell=True)
