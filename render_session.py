#!/usr/bin/python

import subprocess
from argparse import ArgumentParser
import os

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("--args")
parser.add_argument("--visualizer",
                    # default="python visual-experiments/waves.py -width 720 -height 576")
                    default="python visual-experiments/waves.py -width 640 -height 360")
parser.add_argument("-o", "--output", default="export.mp4")

class SessionRenderer:
    def __init__(self,
                 sessiondir,
                 session_args,
                 visualizer,
                 output,
                 temp_dir="."):
        self.sessiondir = sessiondir
        self.session_args = session_args
        self.visualizer = visualizer
        self.output = output
        self.temp_dir = temp_dir
        self.audio_capture_path = "%s/capture.wav" % self.temp_dir

    def render(self):
        self._ensure_temp_dir_exists()
        self._render_audio()
        self._render_video()
        self._create_video_file()

    def _ensure_temp_dir_exists(self):
        if not os.path.exists(self.temp_dir):
            os.mkdir(self.temp_dir)

    def _render_audio(self):
        print "___ Rendering audio ___"
        self._call('./play.py %s --visualizer="%s -sync -capture-message-log=%s/messages.log" --sc-mode=rear_to_front_stereo_reverb --quit-at-end --capture-audio=%s %s' % (
                self.sessiondir,
                self.visualizer,
                self.temp_dir,
                self.audio_capture_path,
                self.session_args))

    def _render_video(self):
        print "___ Rendering video ___"
        self._call('%s -play-message-log=%s/messages.log -standalone -export -export-dir %s/export' % (
                self.visualizer,
                self.temp_dir,
                self.temp_dir))

    def _create_video_file(self):
        print "___ Creating video file ___"
        self._call('avconv -y -f image2 -r 30 -i %s/export/%%07d.png -map 0 -i %s -vcodec libx264 -crf 0 %s -acodec libvo_aacenc -ab 320k' % (
                self.temp_dir,
                self.audio_capture_path,
                self.output))

    def _call(self, command_line):
        print command_line
        subprocess.call(command_line, shell=True)


if __name__ == "__main__":
    args = parser.parse_args()
    SessionRenderer(args.sessiondir, args.args, args.visualizer, args.output).render()

