#!/bin/sh
./revisualize_ancestry.py --geometry=circle sessions/*chester -width 1000 -height 1000 --node-style=circle --unfold=forward -interpret --sway -z 3 --edge-style=line --node-size-envelope=0.5,50,0.2
