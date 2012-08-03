class Gatherer:
    def __init__(self):
        self._pieces = dict()
        self._counter = 1

    def add(self, new_piece):
        overlapping_pieces = self._overlapping_pieces(new_piece)
        if len(overlapping_pieces) > 0:
            new_extension = [new_piece]
            new_extension.extend([self._pieces[key] for key in overlapping_pieces])
            kept_overlapping_piece = self._pieces[overlapping_pieces.pop(0)]
            kept_overlapping_piece.begin = min([piece.begin for piece in new_extension])
            kept_overlapping_piece.end = max([piece.end for piece in new_extension])
            kept_overlapping_piece.byte_size = kept_overlapping_piece.end - kept_overlapping_piece.begin
            for key in overlapping_pieces:
                del self._pieces[key]
        else:
            self._pieces[self._counter] = new_piece
            self._counter += 1

    def pieces(self):
        return self._pieces.values()

    def piece(self, key):
        return self._pieces[key]

    def _overlapping_pieces(self, piece):
        return filter(lambda key: self._pieces_overlap(piece, self._pieces[key]),
                      self._pieces.keys())

    def _pieces_overlap(self, piece1, piece2):
        return ((piece2.begin <= piece1.begin <= piece2.end) or
                (piece2.begin <= piece1.end <= piece2.end) or
                (piece1.begin <= piece2.begin <= piece1.end) or
                (piece1.begin <= piece2.end <= piece1.end))

    def __str__(self):
        return "Gatherer(%s)" % ["Piece(%s,%s)" % (piece.begin, piece.end)
                                 for piece in self._pieces.values()]
