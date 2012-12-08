from ancestry_tracker import AncestryTracker
import sys
import math

class AncestryPlotter:
    LINE = "line"
    CURVE = "curve"
    RECT = "rect"
    CIRCLE = "circle"

    def __init__(self, chunks, options):
        self._chunks = chunks
        self._options = options
        self._tracker = AncestryTracker()
        for chunk in chunks:
            self._tracker.add(chunk)

        self._total_size = max([chunk["end"] for chunk in chunks])
        self._time_end = max([piece.t for piece in self._tracker.last_pieces()])

        if options.edge_style == self.LINE:
            self._edge_plot_method = self._draw_line
        elif options.edge_style == self.CURVE:
            self._edge_plot_method = self._draw_curve

        if options.geometry == self.RECT:
            self._position = self._rect_position
        elif options.geometry == self.CIRCLE:
            self._position = self._circle_position

    def _rect_position(self, t, byte_pos):
        x = t / self._time_end * self._options.width
        y = float(byte_pos) / self._total_size * self._options.height
        return x, y

    def _circle_position(self, t, byte_pos):
        angle = float(byte_pos) / self._total_size * 2*math.pi
        magnitude = (1 - t / self._time_end) * self._options.width / 2
        x = self._options.width / 2 + magnitude * math.cos(angle)
        y = self._options.width / 2 + magnitude * math.sin(angle)
        return x, y

    def plot(self, svg_output=None):
        self._svg_output = svg_output
        self._write_svg('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')
        self._write_svg('<g>')
        self._write_svg('<rect width="%f" height="%f" fill="white" />' % (
            self._options.width, self._options.height))
        self._override_recursion_limit()
        for piece in self._tracker.last_pieces():
            self._follow_piece(piece)
        self._write_svg('</g>')
        self._write_svg('</svg>')

    def _override_recursion_limit(self):
        sys.setrecursionlimit(len(self._chunks))

    def _draw_line(self, x1, y1, x2, y2, color="black"):
        self._write_svg('<line x1="%f" y1="%f" x2="%f" y2="%f" stroke="%s" stroke-width="%f" stroke-opacity="0.5" />' % (
                x1, y1, x2, y2, color, self._options.stroke_width))

    def _draw_curve(self, x1, y1, x2, y2):
        self._write_svg('<path style="stroke:black;stroke-opacity=0.5;fill:none;stroke-width:%f" d="M%f,%f Q%f,%f %f,%f T%f,%f" />' % (
                self._options.stroke_width,
                x1, y1,
                x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.35,
                x1 + (x2 - x1) * 0.55, y1 + (y2 - y1) * 0.65,
                x2, y2))

    def _follow_piece(self, piece):
        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                path.append((older_version.t,
                             (older_version.begin + older_version.end) / 2))
            self._draw_path(path)

        for parent in piece.parents.values():
            self._connect_child_and_parent(
                piece.t, (piece.begin + piece.end) / 2,
                parent.t, (parent.begin + parent.end) / 2)
            self._follow_piece(parent)

    def _connect_child_and_parent(self, t1, b1, t2, b2):
        x1, y1 = self._position(t1, b1)
        x2, y2 = self._position(t2, b2)
        self._edge_plot_method(x1, y1, x2, y2)

    def _write_svg(self, line):
        if self._svg_output:
            print >>self._svg_output, line

    def _draw_path(self, points):
        t0, b0 = points[0]
        x0, y0 = self._position(t0, b0)
        self._write_svg('<path style="stroke:black;stroke-opacity=0.5;fill:none;stroke-width:%f;" d="M%f,%f' % (
                self._options.stroke_width, x0, y0))
        for (t, b) in points[1:]:
            x, y = self._position(t, b)
            self._write_svg(' L%f,%f' % (x, y))
        self._write_svg('" />')
