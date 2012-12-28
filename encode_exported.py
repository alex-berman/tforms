#!/usr/bin/python

from argparse import ArgumentParser
import subprocess

def remove_first_corrupt_frame():
    subprocess.call("rm export/00000.png", shell=True)

def call_ffmpeg():
    global args
    cmd = ["ffmpeg",
           "-r", str(args.fps),
           "-i", "export/%05d.png",
           "-vcodec", "libx264",
           "-vpre", "lossless_max",
           "export.mp4"]
    print " ".join(cmd)
    subprocess.call(cmd)

parser = ArgumentParser()
parser.add_argument("-fps", type=float, default=25)
args = parser.parse_args()

remove_first_corrupt_frame()
call_ffmpeg()
