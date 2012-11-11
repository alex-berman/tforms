#!/bin/sh
# Usage (?): encode.sh <audio-sync-offset> <start> <length>
# Audio sync offset can be detected by the beep in capture.wav
sox capture-mastered.wav capture-trimmed.wav trim $1
rm capture.mp4
glc-play capture.glc -o - -y 1 | ffmpeg  -t $3 -i - -i capture-trimmed.wav -acodec libmp3lame -ab 128k -ac 2 -vcodec libx264 -vpre slow -ss $2 -t $3 capture.mp4
rm capture-trimmed.wav
