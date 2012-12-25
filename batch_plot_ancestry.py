#!/usr/bin/python

import session_library
from ancestry_plotter import *
import subprocess

for session in session_library.get_sessions():
    if session["name"].startswith("A"):
        geometry = CIRCLE

        output_path = "graphs/ancestry_circle_spline/ancestry_%s_%s.svg" % (session["name"], geometry)
        cmdline = "./plot_ancestry.py -width 2000 -stroke-width 6 --geometry=%s -o %s %s --edge-style=spline" % (
            geometry, output_path, session["dir"])

        # output_path = "graphs/ancestry_circle_straight_shrinking/ancestry_%s_%s.svg" % (session["name"], geometry)
        # cmdline = "./plot_ancestry.py -width 2000 -stroke-width 10 --geometry=%s -o %s %s --edge-style=line --stroke-style=shrinking" % (
        #     geometry, output_path, session["dir"])

        print cmdline
        subprocess.call(cmdline, shell=True)

        # for geometry in AncestryPlotter.GEOMETRIES:
        #     output_path = "graphs/ancestry/ancestry_%s_%s.svg" % (session["name"], geometry)
        #     cmdline = "./plot_ancestry.py -width 2000 --geometry=%s -o %s %s" % (
        #         geometry, output_path, session["dir"])
        #     print cmdline
        #     subprocess.call(cmdline, shell=True)
