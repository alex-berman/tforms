#!/usr/bin/python

import subprocess

#RESOLUTION = "-width 1280 -height 720"
RESOLUTION = "-width 1024 -height 768"
#RESOLUTION = "-width 640 -height 360"
FPS = 25

sessions = [
    ("*chopin", "-z 20"),
    ("*adele", "-z 20"),
    ("*TDL4", ""),
#    ("*miracle", "-z 5"),
    ("*gulliver", ""),
    ]

for (session, args) in sessions:
    cmd = "./revisualize_ancestry.py --geometry=circle sessions/%s %s %s --node-style=circle --unfold=forward -interpret --sway --sway-magnitude=0.003 --edge-style=line --line-width=1 --node-size-envelope=0.3,25,0.5 --sway-envelope=0,50,0.5 --node-size=0.003 -export -export-fps=%s" % (session, args, RESOLUTION, FPS)
    subprocess.call(cmd, shell=True)

    cmd = "./encode_exported.py -f -fps %s -fade-out 3.0 sessions/%s Ancestry" % (FPS, session)
    subprocess.call(cmd, shell=True)
