#!/usr/bin/python

import subprocess
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-mode", type=str, default="default_stereo")
args = parser.parse_args()

f = open("sc/engine.sc")
engine = f.read()
f.close()

f = open("sc/%s.sc" % args.mode)
engine += f.read()
f.close()

out = open("sc/_compiled.sc", "w")

f = open("sc/boot.sc")
for line in f:
    line = line.replace("//$ENGINE", engine)
    print >>out, line,
f.close()

out.close()

subprocess.call("sclang sc/_compiled.sc", shell=True)
