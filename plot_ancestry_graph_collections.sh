#!/bin/sh
./batch_plot_ancestry.py --collection ancestry_graph_collection_rect --geometry=rect --args "--canvas-width=210 --canvas-height=297 -width 180 -height 180 -stroke-width 0.2 --node-size=0.3 --edge-style=line --unit=mm"
./batch_plot_ancestry.py --collection ancestry_graph_collection_circle --geometry=circle --args "--canvas-width=210 --canvas-height=297 -width 180 -height 180 -stroke-width 0.2 --node-size=0.3 --edge-style=line --unit=mm"
