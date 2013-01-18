#!/usr/bin/python

import subprocess
import os
import glob

#RESOLUTION = "-width 1280 -height 720"
RESOLUTION = "-width 720 -height 576"
#RESOLUTION = "-width 640 -height 360"
FPS = 25

sessions = [
    # ("*chopin", "-z 20"),
    # ("*adele", "-z 20"),
    # ("*TDL4", ""),
    ("*lord-rings", "-z 7"),
    ("*miracle", "-z 5"),
    ("*gulliver", ""),
    ("*potter", ""),
    ("*frankenstein", ""),
    ("*learn*", ""),
    ("*hunger", ""),
    ]

for (session_pattern, args) in sessions:
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
        cmd = "./revisualize_ancestry.py --geometry=circle %s %s %s --node-style=circle --unfold=forward -interpret --sway --sway-magnitude=0.003 --edge-style=line --line-width=1 --node-size-envelope=0.3,25,0.5 --sway-envelope=0,50,0.5 --node-size=0.003 -export -export-fps=%s" % (session_dir, args, RESOLUTION, FPS)
        subprocess.call(cmd, shell=True)

    video_filename = "rendered/%s_ancestry.mp4" % os.path.basename(session_dir)
    print "encoding into %s" % video_filename
    if os.path.exists(video_filename):
        print "video file exists - skipping"
    else:
        cmd = "./encode_exported.py -f -fps %s -fade-out 3.0 %s Ancestry -o %s" % (
            FPS, session_dir, video_filename)
        print cmd
        subprocess.call(cmd, shell=True)
