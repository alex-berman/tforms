#!/usr/bin/python

import session_library
from ancestry_plotter import *
import subprocess

geometry = CIRCLE

for session in session_library.get_sessions():
    output_path = "graphs/ancestry_shrinking/ancestry_%s_%s.svg" % (session["name"], geometry)
    cmdline = "./plot_ancestry.py -width 2000 --geometry=%s -stroke-width 10 --stroke-style=shrinking -o %s %s" % (
        geometry, output_path, session["dir"])
    print cmdline
    subprocess.call(cmdline, shell=True)
