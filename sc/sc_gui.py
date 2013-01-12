#!/usr/bin/env python

CONFIG_FILENAME = "sc/parameters.config"

import pygtk
import gtk
import cPickle

import os
import sys
sys.path.append(os.path.dirname(__file__) + "/..")
from synth_controller import SynthController

synth = SynthController()

parameters = ["mix", "room", "damp"]

def send_values_to_sc():
    global values
    for parameter, value in values.iteritems():
        synth._send("/set_reverb_%s" % parameter, value)

def value_changed(adj, parameter):
    global values
    values[parameter] = adj.value/100
    send_values_to_sc()
    save_values()

def destroy(widget, data=None):
    gtk.main_quit()

def defalt_values():
    values = {}
    for parameter in parameters:
        values[parameter] = 0.5
    return values

def load_values():
    global values
    try:
        f = open(CONFIG_FILENAME, "rb")
        values = cPickle.load(f)
        f.close()
    except (IOError, EOFError):
        print "Warning: failed to load SC parameters from %s. Using default values." % CONFIG_FILENAME
        values = defalt_values()

def save_values():
    global values
    f = open(CONFIG_FILENAME, "wb")
    cPickle.dump(values, f)
    f.close()


load_values()
send_values_to_sc()
window = gtk.Window(gtk.WINDOW_TOPLEVEL)
window.set_default_size(200, 200)
window.connect("destroy", destroy)

main_box = gtk.HBox(False, 0)

for parameter in parameters:
    adj = gtk.Adjustment(
        value=values[parameter]*100, lower=0, upper=100,
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
