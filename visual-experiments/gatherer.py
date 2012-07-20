class Gatherer:
    def __init__(self):
        self._pieces = dict()
        self._counter = 1

    def add(self, piece):
        if self._fit_piece_in_hole(piece):
            pass
        elif self._append_piece(piece):
            pass
        elif self._prepend_piece(piece):
            pass
        else:
            self._pieces[self._counter] = piece
            self._counter += 1

    def pieces(self):
        return self._pieces.values()

    def _fit_piece_in_hole(self, new_piece):
        appendable_piece_key = self._find_appendable_piece(new_piece)
        if appendable_piece_key:
            prependable_piece_key = self._find_prependable_piece(new_piece)
            if prependable_piece_key:
                prependable_piece = self._pieces[prependable_piece_key]
                del self._pieces[prependable_piece_key]
                self._pieces[appendable_piece_key].append(new_piece)
                self._pieces[appendable_piece_key].append(prependable_piece)
                return True
            
    def _append_piece(self, new_piece):
        appendable_piece = self._find_appendable_piece(new_piece)
        if appendable_piece:
            self._pieces[appendable_piece].append(new_piece)
            return True

    def _find_appendable_piece(self, new_piece):
        for key, piece in self._pieces.iteritems():
            if piece.end == new_piece.begin:
                return key

    def _prepend_piece(self, new_piece):
        prependable_piece = self._find_prependable_piece(new_piece)
        if prependable_piece:
            self._pieces[prependable_piece].prepend(new_piece)
            return True

    def _find_prependable_piece(self, new_piece):
        for key, piece in self._pieces.iteritems():
            if piece.begin == new_piece.end:
                return key

