#!/usr/bin/env python

import pygtk
import gtk

import os
import sys
dirname = os.path.dirname(__file__)
if dirname:
    sys.path.append(dirname + "/..")
else:
    sys.path.append("..")
from synth_controller import SynthController

synth = SynthController()

room_adj = gtk.Adjustment(
    value=50.0, lower=0, upper=100,
    step_incr=1, page_incr=10, page_size=0)

def add_room_slider():
    box = gtk.VBox(False, 0)
    label = gtk.Label("Room")
    label.show()
    box.pack_start(label, False, False, 5)
    room_adj.connect("value_changed", room_value_changed)
    slider = gtk.VScale(room_adj)
    slider.set_inverted(True)
    slider.show()
    box.pack_start(slider, True, True, 5)
    box.show()
    main_box.pack_start(box, False, False, 5)

def room_value_changed(adj):
    synth._send("/set_reverb_room", adj.value/100)

def destroy(widget, data=None):
    gtk.main_quit()

window = gtk.Window(gtk.WINDOW_TOPLEVEL)
window.set_default_size(200, 400)
window.connect("destroy", destroy)

main_box = gtk.HBox(False, 0)

add_room_slider()

main_box.show()
window.add(main_box)
window.show()

if __name__ == '__main__':
    gtk.main()
