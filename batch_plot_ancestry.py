#!/usr/bin/python

import session_library
from ancestry_plotter import AncestryPlotter
import subprocess

for session in session_library.get_sessions():
    for geometry in AncestryPlotter.GEOMETRIES:
        output_path = "graphs/ancestry/ancestry_%s_%s.svg" % (session["name"], geometry)
        cmdline = "./plot_ancestry.py --geometry=%s -o %s %s" % (
            geometry, output_path, session["dir"])
        print cmdline
        subprocess.call(cmdline, shell=True)
