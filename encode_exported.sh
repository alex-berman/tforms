#!/bin/sh
ffmpeg -r 25 -i export/%05d.png -vcodec libx264 -vpre lossless_max export.mp4
