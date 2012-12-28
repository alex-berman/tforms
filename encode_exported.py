#!/usr/bin/python

from argparse import ArgumentParser
import subprocess
import os

def call_ffmpeg():
    global args
    cmd = ["ffmpeg",
           "-r", str(args.fps),
           "-i", "export/%07d.png"]
    if args.fade_out:
        num_frames = len(os.listdir("export"))
        num_fade_frames = int(args.fade_out * args.fps)
        start_frame = num_frames - num_fade_frames
        cmd += [
            "-vf",
            "fade=out:%d:%d" % (start_frame, num_fade_frames)]
    cmd += ["-vcodec", "libx264",
            "-vpre", "lossless_max",
            "export.mp4"]
    print " ".join(cmd)
    subprocess.call(cmd)

def remove_corrupt_first_frame():
    subprocess.call("rm export/0000000.png", shell=True)

parser = ArgumentParser()
parser.add_argument("-fps", type=float, default=25)
parser.add_argument("-fade-out", type=float)
args = parser.parse_args()

remove_corrupt_first_frame()
call_ffmpeg()
