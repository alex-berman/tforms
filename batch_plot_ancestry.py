#!/usr/bin/python

from ancestry_plotter import AncestryPlotter, GEOMETRIES
import subprocess
from argparse import ArgumentParser
import os
import importlib
import glob

def read_collection(module_path):
    collection_module = importlib.import_module(module_path)
    collection = []
    for session_dir in collection_module.collection:
        matches = glob.glob(session_dir)
        if len(matches) == 1:
            collection.append(matches[0])
        elif len(matches) == 0:
            raise Exception("no sessions matching %s" % session_dir)
        else:
            raise Exception("more than one session matching %s" % session_dir)
    return collection

def non_excluded_sessions():
    return ["sessions/%s" % name for name in os.listdir("sessions")
            if not name.startswith("b")]

parser = ArgumentParser()
parser.add_argument("--collection", type=str)
parser.add_argument("--geometry", choices=GEOMETRIES)
parser.add_argument("--args", type=str)
args = parser.parse_args()

if args.collection:
    collection = read_collection(args.collection)
else:
    collection = non_excluded_sessions()

for session_dir in collection:
    session_name = os.path.basename(session_dir)

    output_path = "graphs/ancestry_%s/ancestry_%s_%s.svg" % (args.geometry, session_name, args.geometry)
    cmdline = "./plot_ancestry.py --geometry %s %s -o %s %s" % (
        args.geometry, args.args, output_path, session_dir)

    # output_path = "graphs/ancestry_circle_spline/ancestry_%s_%s.svg" % (session_name, geometry)
    # cmdline = "./plot_ancestry.py -width 2000 -stroke-width 6 --geometry=%s -o %s %s --edge-style=spline" % (
    #     geometry, output_path, session_dir)

    # output_path = "graphs/ancestry_circle_straight_shrinking/ancestry_%s_%s.svg" % (session_name, geometry)
    # cmdline = "./plot_ancestry.py -width 2000 -stroke-width 10 --geometry=%s -o %s %s --edge-style=line --stroke-style=shrinking" % (
    #     geometry, output_path, session_dir)

    print cmdline
    subprocess.call(cmdline, shell=True)

    # for geometry in GEOMETRIES:
    #     output_path = "graphs/ancestry/ancestry_%s_%s.svg" % (session_name, geometry)
    #     cmdline = "./plot_ancestry.py -width 2000 --geometry=%s -o %s %s" % (
    #         geometry, output_path, session_dir)
    #     print cmdline
    #     subprocess.call(cmdline, shell=True)
