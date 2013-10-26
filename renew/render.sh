#!/bin/sh
./render_playlist.py renew.renew_playlist high_quality --visualizer="python visual-experiments/waves_and_heat_map.py -left 0 -top 0 --map-margin=0.7,0,0,0 --waves-margin=0,0,0.3,0 --text-renderer=ftgl --font=fonts/simplex_.ttf --peer-info -aspect 16:9" --args="--leading-pause 3"
