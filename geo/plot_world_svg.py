#!/usr/bin/python

import world

width = 1500.0
height = 1500.0

svg = open('world.svg', 'w')

def draw_path(points):
    x0, y0 = points[0]
    write_svg('<path style="stroke:%s;stroke-opacity=0.5;fill:none;" d="M%f,%f' % (
            "black",
            x0, y0))
    for (x, y) in points[1:]:
        write_svg(' L%f,%f' % (x, y))
    write_svg('" />')

def write_svg(string):
    svg.write(string)
    svg.write('\n')

write_svg('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')
write_svg('<g>')
write_svg('<rect width="%f" height="%f" fill="white" />' % (width, height))

for path in world.World(width, height).paths:
    draw_path(path)

write_svg('</g>')
write_svg('</svg>')

svg.close()

