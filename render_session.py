#!/usr/bin/python

import subprocess
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--args")
parser.add_argument("--visualizer",
                    # default="python visual-experiments/waves.py -width 720 -height 576")
                    default="python visual-experiments/waves.py -width 640 -height 360")
parser.add_argument("-o", "--output", default="export.mp4")

def call(command_line):
    print command_line
    subprocess.call(command_line, shell=True)

def render_session(sessiondir, session_args, visualizer, output):
    print "___ Rendering audio ___"

    call('./play.py %s --visualizer="%s -sync -capture-message-log=messages.log" --sc-mode=rear_to_front_stereo_reverb --quit-at-end --capture-audio %s' % (
            sessiondir,
            visualizer,
            session_args))

    print "___ Rendering video ___"
    call('%s -play-message-log=messages.log -standalone -export' % visualizer)

    print "___ Creating video file ___"
    call('avconv -y -f image2 -r 30 -i export/%%07d.png -map 0 -i capture.wav -vcodec libx264 -crf 0 %s -acodec libvo_aacenc -ab 320k' % output)


if __name__ == "__main__":
    args = parser.parse_args()
    render_session(args.sessiondir, args.args, args.visualizer, args.output)
