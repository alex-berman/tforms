#!/usr/bin/python

from argparse import ArgumentParser
import subprocess
import os

def call_ffmpeg():
    global args
    cmd = ["ffmpeg",
           "-r", str(args.fps),
           "-i", "%s/%%07d.png" % args.render_dir]

    if args.force:
        cmd.append("-y")

    if args.fade_out:
        num_frames = len(os.listdir(args.render_dir))
        num_fade_frames = int(args.fade_out * args.fps)
        start_frame = num_frames - num_fade_frames
        cmd += [
            "-vf",
            "fade=out:%d:%d" % (start_frame, num_fade_frames)]

    cmd += ["-vcodec", "libx264",
            "-vpre", "veryslow",
            "-crf", "0",
            args.output]

    print " ".join(cmd)
    subprocess.call(cmd)

def remove_corrupt_first_frame():
    global args
    subprocess.call("rm %s/0000000.png" % args.render_dir, shell=True)

parser = ArgumentParser()
parser.add_argument("render_dir")
parser.add_argument("-fps", type=float, default=25)
parser.add_argument("-fade-out", type=float)
parser.add_argument("-f", "--force", action="store_true")
parser.add_argument("-o", "--output", type=str)
args = parser.parse_args()

remove_corrupt_first_frame()
call_ffmpeg()
