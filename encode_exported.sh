#!/bin/sh
rm export/00000.png # first frame is corrupt
ffmpeg -r 25 -i export/%05d.png -vcodec libx264 -vpre lossless_max export.mp4
