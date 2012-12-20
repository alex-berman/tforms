#!/usr/bin/python

import GeoIP
import random
from gps import GPS
import world

gi = GeoIP.open("GeoLiteCity.dat",GeoIP.GEOIP_STANDARD)

width = 1500.0
height = 1500.0

gps = GPS(width, height)

f = open('ips_on_world.svg', 'w')

def draw_path(points):
    x0, y0 = points[0]
    write_svg('<path style="stroke:%s;stroke-opacity=0.5;fill:none;" d="M%f,%f' % (
            "blue",
            x0, y0))
    for (x, y) in points[1:]:
        write_svg(' L%f,%f' % (x, y))
    write_svg('" />')

def write_svg(string):
    f.write(string)
    f.write('\n')

write_svg('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')
write_svg('<g>')
write_svg('<rect width="%f" height="%f" fill="white" />' % (width, height))

for path in world.World(width, height).paths:
    draw_path(path)

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

