#!/bin/sh
./sequencer.py --locate-peers --visualizer="python visual-experiments/waves.py -width 800 -height 640 -left 0 -top 0 --peer-info --text-renderer=ftgl --font=fonts/simplex_.ttf --waves-margin=0.01,0,0.065,0 --enable-title" --playlist="textival.textival_playlist" --sc-mode=rear_to_front_4ch_reverb
