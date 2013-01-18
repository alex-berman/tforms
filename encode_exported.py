#!/usr/bin/python

from argparse import ArgumentParser
import subprocess
import os

def call_ffmpeg():
    global args, export_dir
    cmd = ["ffmpeg",
           "-r", str(args.fps),
           "-i", "%s/%%07d.png" % export_dir]

    if args.force:
        cmd.append("-y")

    if args.fade_out:
        num_frames = len(os.listdir(export_dir))
        num_fade_frames = int(args.fade_out * args.fps)
        start_frame = num_frames - num_fade_frames
        cmd += [
            "-vf",
            "fade=out:%d:%d" % (start_frame, num_fade_frames)]

    cmd += ["-vcodec", "libx264",
            "-vpre", "lossless_max",
            args.output]

    print " ".join(cmd)
    subprocess.call(cmd)

def remove_corrupt_first_frame():
    global export_dir
    subprocess.call("rm %s/0000000.png" % export_dir, shell=True)

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("visualizer")
parser.add_argument("-fps", type=float, default=25)
parser.add_argument("-fade-out", type=float)
parser.add_argument("-f", "--force", action="store_true")
parser.add_argument("-o", "--output", type=str)
args = parser.parse_args()

export_dir = "%s/rendered_%s" % (args.sessiondir, args.visualizer)
remove_corrupt_first_frame()
call_ffmpeg()
