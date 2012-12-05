#!/bin/sh

./plot_ancestry.py -width 2000 -height 4000 -stroke_width 6 sessions/*shadow/ -f -o press/torrential_forms1.svg
convert press/torrential_forms1.svg press/torrential_forms1.tiff

./plot_ancestry.py -width 3000 -height 3000 -stroke_width 6 sessions/*too-big-darwin/ -f -o press/torrential_forms2.svg
convert press/torrential_forms2.svg -rotate -90 press/torrential_forms2.tiff
