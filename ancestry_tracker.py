import sys
import copy
import math

class Piece:
    def __init__(self, id, t, begin, end, parents={}, growth=[]):
        self.id = id
        self.t = t
        self.begin = begin
        self.end = end
        self.parents = parents
        self.growth = growth

    def __repr__(self):
        return "Piece(id=%s, t=%s, begin=%s, end=%s, parent_ids=%s)" % (
            self.id, self.t, self.begin, self.end, self.parents.keys())

class AncestryTracker:
    def __init__(self):
        self._pieces = dict()
        self._counter = 1

    def add(self, new_piece):
        overlapping_pieces = self._overlapping_pieces(new_piece)
        if len(overlapping_pieces) > 0:
            if len(overlapping_pieces) > 1:
                replacement_id = self._new_piece_id()
                parents = {}
                for parent_id in overlapping_pieces:
                    parents[parent_id] = self._pieces[parent_id]
                growth = []
            else:
                parent = self._pieces[overlapping_pieces[0]]
                replacement_id = new_piece.id
                parents = copy.copy(parent.parents)
                growth = copy.copy(parent.growth)
                growth.append(parent)

            new_extension = [new_piece]
            new_extension.extend([self._pieces[key] for key in overlapping_pieces])
            for key in overlapping_pieces:
                del self._pieces[key]
            replacement_piece = Piece(
                id = replacement_id,
                t = max([piece.t for piece in new_extension]),
                begin = min([piece.begin for piece in new_extension]),
                end = max([piece.end for piece in new_extension]),
                parents = parents,
                growth = growth)
            self._add_piece(replacement_piece)
        else:
            self._add_piece(new_piece)

    def _add_piece(self, piece):
        if piece.id in self._pieces:
            raise Exception("piece with ID %s already added" % piece.id)
        self._pieces[piece.id] = piece

    def _new_piece_id(self):
        new_id = "n%d" % self._counter
        self._counter += 1
        return new_id

    def last_pieces(self):
        return self._pieces.values()

    def _overlapping_pieces(self, piece):
        return filter(lambda key: self._pieces_overlap(piece, self._pieces[key]),
                      self._pieces.keys())

    def _pieces_overlap(self, piece1, piece2):
        return ((piece2.begin <= piece1.begin <= piece2.end) or
                (piece2.begin <= piece1.end <= piece2.end) or
                (piece1.begin <= piece2.begin <= piece1.end) or
                (piece1.begin <= piece2.end <= piece1.end))


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
            self._tracker.add(Piece(chunk["id"], chunk["t"], chunk["begin"], chunk["end"]))

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
