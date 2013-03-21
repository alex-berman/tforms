#!/bin/sh
./sequencer.py --locate-peers --visualizer="python visual-experiments/waves_and_heat_map.py -width 800 -height 640 -left 0 -top 0 --map-margin=0.7,0,0,0 --waves-margin=0,0,0.3,0 --text-renderer=ftgl --font=fonts/simplex_.ttf --peer-info" --playlist="textival.textival_playlist" --sc-mode=rear_to_front_4ch_reverb
