from ancestry_tracker import AncestryTracker, Piece
import sys
import math

class AncestryPlotter:
    LINE = "line"
    CURVE = "curve"
    RECT = "rect"
    CIRCLE = "circle"
    GEOMETRIES = [RECT, CIRCLE]

    def __init__(self, total_size, duration, args):
        self._total_size = total_size
        self._duration = duration
        self._args = args
        self._tracker = AncestryTracker()
        self._num_pieces = 0

        if args.edge_style == self.LINE:
            self._edge_plot_method = self.draw_line
        elif args.edge_style == self.CURVE:
            self._edge_plot_method = self.draw_curve

        if args.geometry == self.RECT:
            self._position = self._rect_position
        elif args.geometry == self.CIRCLE:
            self._position = self._circle_position

    def set_size(self, width, height):
        self._width = width
        self._height = height

    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("--edge-style",
                            choices=[AncestryPlotter.LINE, AncestryPlotter.CURVE],
                            default=AncestryPlotter.CURVE)
        parser.add_argument("--geometry",
                            choices=AncestryPlotter.GEOMETRIES,
                            default=AncestryPlotter.GEOMETRIES[0])

    def add_piece(self, piece_id, t, begin, end):
        self._tracker.add(Piece(piece_id, t, begin, end))
        self._num_pieces += 1

    def _rect_position(self, t, byte_pos):
        x = t / self._duration * self._width
        y = float(byte_pos) / self._total_size * self._height
        return x, y

    def _circle_position(self, t, byte_pos):
        angle = float(byte_pos) / self._total_size * 2*math.pi
        magnitude = (1 - t / self._duration) * self._width / 2
        x = self._width / 2 + magnitude * math.cos(angle)
        y = self._width / 2 + magnitude * math.sin(angle)
        return x, y

    def plot(self):
        self._override_recursion_limit()
        for piece in self._tracker.last_pieces():
            self._follow_piece(piece)

    def _override_recursion_limit(self):
        sys.setrecursionlimit(max(self._num_pieces, sys.getrecursionlimit()))

    def _follow_piece(self, piece):
        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                path.append((older_version.t,
                             (older_version.begin + older_version.end) / 2))
            self.draw_path(path)

        for parent in piece.parents.values():
            self._connect_child_and_parent(
                piece.t, (piece.begin + piece.end) / 2,
                parent.t, (parent.begin + parent.end) / 2)
            self._follow_piece(parent)

    def _connect_child_and_parent(self, t1, b1, t2, b2):
        x1, y1 = self._position(t1, b1)
        x2, y2 = self._position(t2, b2)
        self._edge_plot_method(x1, y1, x2, y2)


class AncestrySvgPlotter(AncestryPlotter):
    def set_size(self, width, height):
        if width is None:
            width = 500
        if height is None:
            if self._args.geometry == self.RECT:
                height = int(width * self._total_size / self._duration * 0.000005)
            else:
                height = width
        AncestryPlotter.set_size(self, width, height)

    def plot(self, svg_output=None):
        self._svg_output = svg_output
        self._write_svg('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')
        self._write_svg('<g>')
        self._write_svg('<rect width="%f" height="%f" fill="white" />' % (
            self._width, self._height))
        AncestryPlotter.plot(self)
        self._write_svg('</g>')
        self._write_svg('</svg>')

    def draw_line(self, x1, y1, x2, y2, color="black"):
        self._write_svg('<line x1="%f" y1="%f" x2="%f" y2="%f" stroke="%s" stroke-width="%f" stroke-opacity="0.5" />' % (
                x1, y1, x2, y2, color, self._args.stroke_width))

    def draw_curve(self, x1, y1, x2, y2):
        self._write_svg('<path style="stroke:black;stroke-opacity=0.5;fill:none;stroke-width:%f" d="M%f,%f Q%f,%f %f,%f T%f,%f" />' % (
                self._args.stroke_width,
                x1, y1,
                x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.35,
                x1 + (x2 - x1) * 0.55, y1 + (y2 - y1) * 0.65,
                x2, y2))

    def draw_path(self, points):
        t0, b0 = points[0]
        x0, y0 = self._position(t0, b0)
        self._write_svg('<path style="stroke:black;stroke-opacity=0.5;fill:none;stroke-width:%f;" d="M%f,%f' % (
                self._args.stroke_width, x0, y0))
        for (t, b) in points[1:]:
            x, y = self._position(t, b)
            self._write_svg(' L%f,%f' % (x, y))
        self._write_svg('" />')

    def _write_svg(self, line):
        if self._svg_output:
            print >>self._svg_output, line
