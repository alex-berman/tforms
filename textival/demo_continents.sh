#!/bin/sh
./play.py --locate-peers --visualizer="python visual-experiments/waves_and_heat_map.py -width 800 -height 640 -left 0 -top 0 --peer-info --map-margin=0.74,0,0,0 --waves-margin=0,0,0.3,0 --hscope=0.3:0.8 --vscope=0.07:0.4 --continents --text-renderer=ftgl --font=fonts/simplex_.ttf" sessions/*roda_rummet1 --pretend-audio=textival/audio/strindberg_brott_och_brott1.wav -z 1 --sc-mode=rear_to_front_4ch_reverb --title="Karin Boye: Kallocain (del 1)"
