#!/bin/sh
./play.py --predecode --visualizer="python visual-experiments/stairs_step_is_partition.py -waveform -waveform-gain 2 -camera-script=camera_script" sessions/*TDL4-slow --max-pause-within-segment=3 --output=ssr
