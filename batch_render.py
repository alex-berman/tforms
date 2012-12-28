#!/usr/bin/python

import subprocess

#RESOLUTION = "-width 1280 -height 720"
RESOLUTION = "-width 640 -height 360"
FPS = 25

sessions = [
    ("*chopin", "-z 20"),
    ("*adele", "-z 20"),
    ]

for (session, args) in sessions:
    cmd = "./revisualize_ancestry.py --geometry=circle sessions/%s %s %s --node-style=circle --unfold=forward -interpret --sway --edge-style=line --line-width=1 --node-size-envelope=0.5,10,0.5 --sway-envelope=0,50,0.5 --node-size=0.003 -export -export-fps=%s" % (session, args, RESOLUTION, FPS)
    subprocess.call(cmd, shell=True)

    cmd = "./encode_exported.py -f -r %s sessions/%s Ancestry" % (FPS, session)
    subprocess.call(cmd, shell=True)
