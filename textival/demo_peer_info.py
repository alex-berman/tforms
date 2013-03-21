#!/bin/sh
./play.py --locate-peers --visualizer="python visual-experiments/waves.py -width 800 -height 640 -left 0 -top 0 --peer-info --text-renderer=ftgl --font=fonts/simplex_.ttf --waves-margin=0.01,0,0.065,0 --enable-title" sessions/*roda_rummet1 --pretend-audio=textival/audio/strindberg_brott_och_brott1.wav -z 1 --sc-mode=rear_to_front_4ch_reverb --title="Karin Boye: Kallocain (del 1)"
