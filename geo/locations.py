import cPickle
import os

def get_locations():
    f = open("%s/scanner/locations.dat" % os.path.dirname(os.path.realpath(__file__)), "r")
    locations = cPickle.load(f)
    f.close()
    return locations

