#!/bin/sh
#nice python circular_puzzle.py -sync &
nice python stairs_step_is_partition.py -sync -waveform -waveform-gain 2 -camera-script=camera_script &
#jack_rec -f capture.wav SuperCollider:out_1 SuperCollider:out_2 -d -1
jack_rec -f capture.wav Binaural-Renderer:out_left Binaural-Renderer:out_right -d -1
