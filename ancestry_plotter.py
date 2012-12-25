from ancestry_tracker import AncestryTracker, Piece
import sys
import math
from bezier import make_bezier
from vector import Vector2d

CURVE_PRECISION = 50

LINE = "line"
CURVE = "curve"
SPLINE = "spline"
RECT = "rect"
CIRCLE = "circle"
GEOMETRIES = [RECT, CIRCLE]
PLAIN = "plain"
SHRINKING = "shrinking"

class AncestryPlotter:
    def __init__(self, total_size, duration, args):
        self._total_size = total_size
        self._duration = duration
        self._args = args
        self._tracker = AncestryTracker()
        self._num_pieces = 0

        if args.output_type != "dot":
            if args.edge_style == LINE:
                if args.stroke_style == SHRINKING:
                    self._edge_plot_method = self.draw_shrinking_line
                else:
                    self._edge_plot_method = self.draw_line
            elif args.edge_style in [CURVE, SPLINE]:
                if args.stroke_style == SHRINKING:
                    self._edge_plot_method = self.draw_shrinking_curve
                else:
                    self._edge_plot_method = self.draw_curve

            if args.stroke_style == SHRINKING:
                self._path_plot_method = self._draw_shrinking_path
            else:
                self._path_plot_method = self.draw_path

            if args.geometry == RECT:
                self._position = self._rect_position
            elif args.geometry == CIRCLE:
                self._position = self._circle_position

    def set_size(self, width, height):
        self._width = width
        self._height = height

    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("--edge-style",
                            choices=[LINE, CURVE, SPLINE],
                            default=CURVE)
        parser.add_argument("--geometry",
                            choices=GEOMETRIES,
                            default=GEOMETRIES[0])
        parser.add_argument("--stroke-style",
                            choices=[PLAIN, SHRINKING])
        parser.add_argument("-stroke-width", type=float, default=1)
        parser.add_argument("--output-type", choices=OUTPUT_TYPES.keys(),
                            default="svg")

    def add_piece(self, piece_id, t, begin, end):
        self._tracker.add(Piece(piece_id, t, begin, end))
        self._num_pieces += 1

    def _rect_position(self, t, byte_pos):
        x = t / self._duration * self._width
        y = float(byte_pos) / self._total_size * self._height
        return Vector2d(x, y)

    def _circle_position(self, t, byte_pos):
        angle = float(byte_pos) / self._total_size * 2*math.pi
        x = self._width / 2 + (1 - t / self._duration) * self._width / 2 * math.cos(angle)
        y = self._height / 2 + (1 - t / self._duration) * self._height / 2 * math.sin(angle)
        return Vector2d(x, y)

    def plot(self):
        self._override_recursion_limit()
        for piece in self._tracker.last_pieces():
            self._follow_piece(piece)

    def _override_recursion_limit(self):
        sys.setrecursionlimit(max(self._num_pieces, sys.getrecursionlimit()))

    def _follow_piece(self, piece, child=None):
        self.plot_piece(piece)
        if len(piece.growth) > 0:
            path = [(piece.t,
                    (piece.begin + piece.end) / 2)]
            for older_version in reversed(piece.growth):
                path.append((older_version.t,
                             (older_version.begin + older_version.end) / 2))
            self._path_plot_method(path)

        for parent in piece.parents.values():
            self._connect_generations(parent, piece, child)
            self._follow_piece(parent, piece)

    def plot_piece(self, piece):
        pass

    def _connect_generations(self, parent, child, grandchild):
        parent_pos = self._position(parent.t, (parent.begin + parent.end) / 2)
        child_pos = self._position(child.t, (child.begin + child.end) / 2)
        self._stroke_width1 = self._stroke_width_at_time(child.t)
        self._stroke_width2 = self._stroke_width_at_time(parent.t)

        if self._args.edge_style == SPLINE and grandchild is not None:
            grandchild_pos = self._position(grandchild.t, (grandchild.begin + grandchild.end) / 2)
            control_point = self._spline_control_point(parent_pos, child_pos, grandchild_pos)
            self._draw_spline(parent_pos, child_pos, control_point)
        else:
            self._edge_plot_method(child_pos.x, child_pos.y, parent_pos.x, parent_pos.y)

    def _spline_control_point(self, parent, child, grandchild):
        return grandchild + (child - grandchild)*1.3
        parent1 = parent - child
        grandchild1 = grandchild - child
        angle = grandchild.angle().get()
        parent2 = parent1.rotate(-angle)

        control_point2 = Vector2d(parent2.x, 0)
        control_point1 = control_point2.rotate(angle)
        control_point = control_point1 + child
        print "angle=%s mag=%s\n%s\n%s\n%s\n%s\n\n" % ((parent-child).angle().get()*math.pi*2, (parent-child).mag(), parent, child, grandchild, control_point)
        return control_point

    def _draw_spline(self, p1, p2, p_control):
        self._write_svg('<path style="stroke:%s;stroke-opacity=0.5;fill:none;stroke-width:%f" d="M%f,%f Q%f,%f %f,%f" />' % (
                self._args.stroke_color,
                self._args.stroke_width,
                p1.x, p1.y,
                p_control.x, p_control.y,
                p2.x, p2.y))

    def _stroke_width_at_time(self, t):
        return self._args.stroke_width * (1 - pow(t/self._duration, 0.6))


class AncestrySvgPlotter(AncestryPlotter):
    def set_size(self, width, height):
        if width is None:
            width = 500
        if height is None:
            if self._args.geometry == RECT:
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

    def draw_line(self, x1, y1, x2, y2):
        self._write_svg('<line x1="%f" y1="%f" x2="%f" y2="%f" style="stroke:%s;stroke-opacity=0.5;fill:none;stroke-width:%f" />' % (
                x1, y1, x2, y2, self._args.stroke_color, self._args.stroke_width))

    def draw_shrinking_line(self, x1, y1, x2, y2):
        stroke_points = [(x1, y1),
                         (x2, y2)]
        self._draw_shrinking_path_xy(stroke_points)

    def draw_curve(self, x1, y1, x2, y2):
        self._write_svg('<path style="stroke:%s;stroke-opacity=0.5;fill:none;stroke-width:%f" d="M%f,%f Q%f,%f %f,%f T%f,%f" />' % (
                self._args.stroke_color,
                self._args.stroke_width,
                x1, y1,
                x1 + (x2 - x1) * 0.45, y1 + (y2 - y1) * 0.35,
                x1 + (x2 - x1) * 0.55, y1 + (y2 - y1) * 0.65,
                x2, y2))

    def draw_shrinking_curve(self, x1, y1, x2, y2):
        control_points = [
            Vector2d(x1, y1),
            Vector2d(x1 + (x2 - x1) * 0.3, y1),
            Vector2d(x1 + (x2 - x1) * 0.7, y2),
            Vector2d(x2, y2)
            ]
        bezier = make_bezier([(p.x, p.y) for p in control_points])
        stroke_points = bezier(CURVE_PRECISION)
        self._draw_shrinking_path_xy(stroke_points)

    def _draw_shrinking_path_xy(self, stroke_points):
        outline_pairs = self._outline(stroke_points)
        x0, y0 = stroke_points[0]
        self._write_svg('<path style="fill:%s;stroke:none;stroke-opacity:0.5;" d="M%f,%f' % (
                self._args.stroke_color,
                x0, y0))
        for pair in outline_pairs:
            x, y = pair[0]
            self._write_svg(' L%f,%f' % (x, y))
        for pair in reversed(outline_pairs):
            x, y = pair[1]
            self._write_svg(' L%f,%f' % (x, y))
        self._write_svg('" />')

    def _outline(self, stroke_points):
        return [self._outline_pair(stroke_points, n) for n in range(len(stroke_points))]

    def _outline_pair(self, stroke_points, n):
        angle = self._stroke_angle(stroke_points, n)
        angle1 = angle + math.pi/2
        angle2 = angle - math.pi/2
        x, y = stroke_points[n]
        width = self._stroke_width1 + (self._stroke_width2 - self._stroke_width1) * \
            (float(n) / (len(stroke_points)-1))
        p1 = (x + math.cos(angle1) * width,
              y + math.sin(angle1) * width)
        p2 = (x + math.cos(angle2) * width,
              y + math.sin(angle2) * width)
        return (p1, p2)

    def _stroke_angle(self, stroke_points, n):
        n1 = max(0, n-1)
        n2 = min(len(stroke_points)-1, n+1)
        x1, y1 = stroke_points[n1]
        x2, y2 = stroke_points[n2]
        return math.atan2(y1-y2, x1-x2)

    def draw_path(self, points):
        t0, b0 = points[0]
        x0, y0 = self._position(t0, b0)
        self._write_svg('<path style="stroke:%s;stroke-opacity=0.5;fill:none;stroke-width:%f;" d="M%f,%f' % (
                self._args.stroke_color,
                self._args.stroke_width,
                x0, y0))
        for (t, b) in points[1:]:
            x, y = self._position(t, b)
            self._write_svg(' L%f,%f' % (x, y))
        self._write_svg('" />')

    def _draw_shrinking_path(self, path):
        t1 = path[0][0]
        t2 = path[-1][0]
        self._stroke_width1 = self._stroke_width_at_time(t1)
        self._stroke_width2 = self._stroke_width_at_time(t2)
        path_xy = [self._position(t, b) for (t, b) in path]
        self._draw_shrinking_path_xy(path_xy)

    def _write_svg(self, line):
        if self._svg_output:
            print >>self._svg_output, line


class AncestryDotPlotter(AncestryPlotter):
    def plot(self, output):
        self._output = output
        self._write("digraph G {")
        self._write("  node [shape=point];")
        self._write("  edge [arrowhead=none];")
        AncestryPlotter.plot(self)
        self._write("}")

    def plot_piece(self, piece):
        self._write("  n%s;" % piece.id)

    def _connect_generations(self, parent, child, grandchild):
        self._write("  n%s -> n%s;" % (child.id, parent.id))

    def _path_plot_method(self, path):
        pass

    def _write(self, line):
        print >>self._output, line
        print >>self._output, "\n"


OUTPUT_TYPES = {"svg": AncestrySvgPlotter,
                "dot": AncestryDotPlotter}
