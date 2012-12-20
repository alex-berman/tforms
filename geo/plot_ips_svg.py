#!/usr/bin/python

import GeoIP
import random
from gps import GPS

gi = GeoIP.open("GeoLiteCity.dat",GeoIP.GEOIP_STANDARD)

width = 1500.0
height = 1500.0

gps = GPS(width, height)

f = open('geo.svg', 'w')

def write_svg(string):
    f.write(string)
    f.write('\n')

write_svg('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')
write_svg('<g>')
write_svg('<rect width="%f" height="%f" fill="white" />' % (width, height))

n = 0
while n < 100000:
    addr = ".".join([str(random.randint(0,255)) for i in range(4)])
    gir = gi.record_by_addr(addr)
    if gir:
        x = gps.x(gir['longitude'])
        y = gps.y(gir['latitude'])
        write_svg('<rect x="%f" y="%f" stroke="black" style="stroke-opacity:1%%" width="1" height="1" />\n' % (x, y))
        n += 1

write_svg('</g>')
write_svg('</svg>')

f.close()

