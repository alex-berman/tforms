#!/bin/sh
./revisualize_ancestry.py --geometry=circle sessions/*chester -z 3 -width 1280 -height 720 --node-style=circle --unfold=forward -interpret --sway --edge-style=line --line-width=1 --node-size-envelope=0.5,10,0.5 --sway-envelope=0,50,0.5 --node-size=0.003
