#!/bin/sh
# Usage: run play.py with the flag --visualize first, then start capture.sh in a separate terminal
# After completion, master capture.wav and save it as capture-mastered.wav. Then run encode.sh.
glc-capture -s --crop=640x480+30+30 --capture=back -o capture.glc ./visualize_and_rec_audio.sh
