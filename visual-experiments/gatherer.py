
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
            kept_overlapping_piece.torrent_begin = min([piece.torrent_begin for piece in new_extension])
            kept_overlapping_piece.torrent_end = max([piece.torrent_end for piece in new_extension])
            kept_overlapping_piece.byte_size = \
                kept_overlapping_piece.torrent_end - kept_overlapping_piece.torrent_begin
            kept_overlapping_piece.begin = \
                kept_overlapping_piece.torrent_begin - kept_overlapping_piece.f.offset
            kept_overlapping_piece.end = \
                kept_overlapping_piece.torrent_end - kept_overlapping_piece.f.offset
            for key in overlapping_pieces:
                del self._pieces[key]
        else:
            self._pieces[self._counter] = new_piece
            self._counter += 1

    def would_append(self, new_piece):
        for key in self._overlapping_pieces(new_piece):
            overlapping_piece = self._pieces[key]
            if overlapping_piece.torrent_end <= new_piece.torrent_begin:
                return overlapping_piece

    def pieces(self):
        return self._pieces.values()

    def piece(self, key):
        return self._pieces[key]

    def _overlapping_pieces(self, piece):
        return filter(lambda key: self._pieces_overlap(piece, self._pieces[key]),
                      self._pieces.keys())

    def _pieces_overlap(self, piece1, piece2):
        return ((piece2.torrent_begin <= piece1.torrent_begin <= piece2.torrent_end) or
                (piece2.torrent_begin <= piece1.torrent_end <= piece2.torrent_end) or
                (piece1.torrent_begin <= piece2.torrent_begin <= piece1.torrent_end) or
                (piece1.torrent_begin <= piece2.torrent_end <= piece1.torrent_end))

    def __str__(self):
        return "Gatherer(%s)" % ["Piece(%s,%s)" % (piece.torrent_begin, piece.torrent_end)
                                 for piece in self._pieces.values()]
