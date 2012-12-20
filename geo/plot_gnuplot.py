#!/usr/bin/python

#gnuplot:
#plot "plot.dat" with dots

import GeoIP
import random

gi = GeoIP.open("/home/alex/install/geo/GeoLiteCity.dat",GeoIP.GEOIP_STANDARD)

width = 100.0
height = 100.0

f = open("plot.dat", "w")

n = 0
while n < 100000:
    addr = ".".join([str(random.randint(0,255)) for i in range(4)])
    gir = gi.record_by_addr(addr)
    if gir:
        x = ((gir['longitude'] + 180) * (width / 360))
        y = -(((gir['latitude'] * -1) + 90) * (height / 180))
        f.write("%f, %f\n" % (x, y))
        n += 1

f.close()

