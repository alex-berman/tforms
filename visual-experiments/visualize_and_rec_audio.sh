#!/bin/sh
nice python merging_puzzle.py -sync &
jack_rec -f capture.wav SuperCollider:out_1 SuperCollider:out_2 -d -1