#!/bin/sh
python upscaled_arrivals.py &
jack_rec -f capture.wav SuperCollider:out_1 SuperCollider:out_2 -d -1
