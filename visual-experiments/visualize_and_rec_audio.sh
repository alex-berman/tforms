#!/bin/sh
nice python circular_puzzle.py -sync &
jack_rec -f capture.wav SuperCollider:out_1 SuperCollider:out_2 -d -1
