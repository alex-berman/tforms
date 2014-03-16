import copy
from logger_factory import logger

class Piece:
    def __init__(self, id, t, begin, end, parents={}, growth=[]):
        self.id = id
        self.t = t
        self.begin = begin
        self.end = end
        self.parents = parents
        self.growth = growth

    def __repr__(self):
        return "Piece(id=%s, t=%s, begin=%s, end=%s, parent_ids=%s, growth=%s)" % (
            self.id, self.t, self.begin, self.end, self.parents.keys(),
            [piece.compact_str() for piece in self.growth])

    def compact_str(self):
        return "Piece(id=%s, t=%s, begin=%s, end=%s, parent_ids=%s)" % (
            self.id, self.t, self.begin, self.end, self.parents.keys())


class AncestryTracker:
    def __init__(self):
        self._pieces = dict()
        self._counter = 1
        self.growth_time_limit = None

    def add(self, new_piece):
        logger.info("add(%s)" % new_piece)
        overlapping_pieces = self._overlapping_pieces(new_piece)
        if len(overlapping_pieces) > 0:
            if len(overlapping_pieces) > 1:
                self._add_generation(new_piece, overlapping_pieces)
            else:
                parent = self._pieces[overlapping_pieces[0]]
                if self.growth_time_limit is None or (new_piece.t - parent.t) < self.growth_time_limit:
                    self._grow(new_piece, overlapping_pieces)
                else:
                    self._add_generation(new_piece, overlapping_pieces)
        else:
            logger.info("new piece %s" % new_piece)
            self._add_piece(new_piece)

    def _add_generation(self, new_piece, overlapping_pieces):
        replacement_id = self._new_piece_id()
        parents = {}
        for parent_id in overlapping_pieces:
            parents[parent_id] = self._pieces[parent_id]
        growth = []

        new_extension = [new_piece]
        new_extension.extend([self._pieces[key] for key in overlapping_pieces])
        replacement_piece = Piece(
            id = replacement_id,
            t = max([piece.t for piece in new_extension]),
            begin = min([piece.begin for piece in new_extension]),
            end = max([piece.end for piece in new_extension]),
            parents = parents,
            growth = growth)
        self._replace(overlapping_pieces, replacement_piece)

    def _grow(self, new_piece, overlapping_pieces):
        parent_id = overlapping_pieces[0]
        parent = self._pieces[parent_id]
        new_extension = [new_piece, parent]
        replacement_begin = min([piece.begin for piece in new_extension])
        replacement_end = max([piece.end for piece in new_extension])
        if replacement_begin != parent.begin or replacement_end != parent.end:
            replacement_piece = copy.copy(parent)
            replacement_piece.id = new_piece.id
            replacement_piece.growth = copy.copy(parent.growth)
            replacement_piece.growth.append(parent)
            replacement_piece.t = max([piece.t for piece in new_extension])
            replacement_piece.begin = replacement_begin
            replacement_piece.end = replacement_end
            self._replace([parent_id], replacement_piece)

    def _replace(self, old_piece_ids, replacement_piece):
        logger.info("_replacing\n%s\nwith %s" % (
                "\n".join([str(self._pieces[piece_id]) for piece_id in old_piece_ids]),
                replacement_piece))
        for old_piece_id in old_piece_ids:
            del self._pieces[old_piece_id]
        self._add_piece(replacement_piece)

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

    def pieces(self):
        return self._pieces
