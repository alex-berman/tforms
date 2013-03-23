#!/usr/bin/env python
import subprocess
L_MARGIN = R_MARGIN = 0.05
subprocess.call('./sequencer.py --locate-peers --visualizer="python visual-experiments/waves_and_heat_map.py -width 1920 -height 1080 -left 0 -top 0 --map-margin=0.7,%f,0,%f --waves-margin=0,%f,0.3,%f --text-renderer=ftgl --font=fonts/simplex_.ttf --peer-info" --playlist="textival.textival_playlist" --sc-mode=rear_to_front_4ch_reverb' % (R_MARGIN, L_MARGIN, R_MARGIN, L_MARGIN), shell=True)
