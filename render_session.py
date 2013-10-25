#!/usr/bin/python

import subprocess
from argparse import ArgumentParser
import os

profiles = {
    "high_quality": {
        "format": "mp4",
        "width": 1024,
        "height": 768,
        "frame_rate": 50,
        "video_encoding_options": "-vcodec libx264 -crf 0",
        "audio_encoding_options": "-acodec libvo_aacenc -ab 320k"
        },
    "divx": {
        "format": "avi",
        "width": 720,
        "height": 576,
        "frame_rate": 25,
        "video_encoding_options": "-vcodec mpeg4 -g 300 -vtag DX50 -trellis 1 -mbd 2 -b 6000000",
        "audio_encoding_options": "-acodec libmp3lame -ab 224000"
        },
    }

parser = ArgumentParser()
parser.add_argument("sessiondir")
parser.add_argument("profile", choices=profiles.keys())
parser.add_argument("--args")
parser.add_argument("--visualizer",
                    default="python visual-experiments/waves.py")
parser.add_argument("-o", "--output", default="export")
parser.add_argument("-f", "--force", action="store_true")

class SessionRenderer:
    def __init__(self,
                 sessiondir,
                 session_args,
                 visualizer,
                 output_without_extension,
                 profile_name,
                 force,
                 temp_dir="."):
        self.sessiondir = sessiondir
        self.session_args = session_args
        self.visualizer = visualizer
        self.temp_dir = temp_dir
        self.profile = profiles[profile_name]
        self.force = force
        self.output = "%s.%s" % (output_without_extension, self.profile["format"])
        self.audio_capture_path = "%s/capture.wav" % self.temp_dir
        self.message_log_path = "%s/messages.log" % self.temp_dir
        self.video_frames_dir = "%s/export" % self.temp_dir

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
        if self._should_render_audio():
            self._call('./play.py %s --visualizer="%s -width %s -height %s -sync -capture-message-log=%s" --sc-mode=rear_to_front_stereo_reverb --quit-at-end --capture-audio=%s --locate-peers %s' % (
                    self.sessiondir,
                    self.visualizer,
                    self.profile["width"],
                    self.profile["height"],
                    self.message_log_path,
                    self.audio_capture_path,
                    self.session_args))
        else:
            print "(up-to-date)"

    def _should_render_audio(self):
        return self.force or not os.path.exists(self.audio_capture_path)

    def _render_video(self):
        print "___ Rendering video ___"
        if self._should_render_video():
            self._call('%s -width %s -height %s -export-fps %s -play-message-log=%s -standalone -export -export-dir %s' % (
                    self.visualizer,
                    self.profile["width"],
                    self.profile["height"],
                    self.profile["frame_rate"],
                    self.message_log_path,
                    self.video_frames_dir))
        else:
            print "(up-to-date)"

    def _should_render_video(self):
        return self.force or \
            ((not os.path.exists(self.video_frames_dir)) or
             self._older(self.video_frames_dir, self.audio_capture_path) or
             self._older(self.video_frames_dir, self.message_log_path))

    def _create_video_file(self):
        print "___ Creating video file ___"
        if self._should_create_video_file():
            self._call(
                'avconv -y -f image2 -r %s -i %s/%%07d.png -map 0 -i %s %s %s %s' \
                    % (self.profile["frame_rate"],
                       self.video_frames_dir,
                       self.audio_capture_path,
                       self.profile["video_encoding_options"],
                       self.profile["audio_encoding_options"],
                       self.output))
        else:
            print "(up-to-date)"

    def _should_create_video_file(self):
        return self.force or \
            ((not os.path.exists(self.output)) or
             self._older(self.output, self.audio_capture_path) or
             self._older(self.output, self.video_frames_dir))

    def _older(self, path1, path2):
        return os.path.getmtime(path1) < os.path.getmtime(path2)

    def _call(self, command_line):
        print command_line
        subprocess.call(command_line, shell=True)


if __name__ == "__main__":
    args = parser.parse_args()
    SessionRenderer(
        args.sessiondir,
        args.args,
        args.visualizer,
        args.output,
        args.profile,
        args.force).render()
