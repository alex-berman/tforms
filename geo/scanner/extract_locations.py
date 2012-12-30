#!/usr/bin/python

import sys
import re
import cPickle

sys.path.append("..")
from ip_locator import IpLocator

ip_locator = IpLocator()
locations = []
f = open("peers.log")
r = re.compile('^peer \[([0-9.]+)\]')
for line in f:
    m = r.search(line)
    if m:
        addr = m.group(1)
        location = ip_locator.locate(addr)
        if location:
            locations.append(location)
f.close()

out = open("locations.dat", "w")
cPickle.dump(locations, out)
out.close()
