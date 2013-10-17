#!/usr/bin/python

import subprocess
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("-args")
args = parser.parse_args()

def call(command_line):
    print command_line
    subprocess.call(command_line, shell=True)


print "___ Rendering audio ___"

call('./play.py %s --visualizer="python visual-experiments/waves.py -width 720 -height 576 -sync -capture-message-log=messages.log" --sc-mode=rear_to_front_stereo_reverb --quit-at-end --capture-audio %s' % (
        args.sessiondir,
        args.args))


print "___ Rendering video ___"

call('python visual-experiments/waves.py -width 720 -height 576 -play-message-log=messages.log -standalone -export')


print "___ Creating video file ___"

call('avconv -y -f image2 -r 30 -i export/%07d.png -map 0 -i capture.wav -vcodec libx264 -crf 0 export.mp4 -acodec libvo_aacenc -ab 320k')
