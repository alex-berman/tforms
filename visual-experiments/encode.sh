#!/bin/sh
glc-play capture.glc -o - -y 1 | ffmpeg -i - -i capture.wav -acodec libmp3lame -ab 128k -ac 2 -vcodec libx264 -vpre slow -crf 22 -threads 0 capture.mp4
