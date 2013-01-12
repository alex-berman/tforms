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

parameters = ["mix", "room", "damp"]

def value_changed(adj, parameter):
    synth._send("/set_reverb_%s" % parameter, adj.value/100)

def destroy(widget, data=None):
    gtk.main_quit()

window = gtk.Window(gtk.WINDOW_TOPLEVEL)
window.set_default_size(200, 200)
window.connect("destroy", destroy)

main_box = gtk.HBox(False, 0)

for parameter in parameters:
    adj = gtk.Adjustment(
        value=50.0, lower=0, upper=100,
        step_incr=1, page_incr=10, page_size=0)

    box = gtk.VBox(False, 0)
    label = gtk.Label(parameter)
    label.show()
    box.pack_start(label, False, False, 10)
    adj.connect("value_changed", value_changed, parameter)
    slider = gtk.VScale(adj)
    slider.set_inverted(True)
    slider.show()
    box.pack_start(slider, True, True, 5)
    box.show()
    main_box.pack_start(box, False, False, 10)

main_box.show()
window.add(main_box)
window.show()

if __name__ == '__main__':
    gtk.main()
