class Gatherer:
    def __init__(self):
        self._pieces = []

    def add(self, piece):
        if self._append_piece(piece):
            pass
        elif self._prepend_piece(piece):
            pass
        else:
            self._pieces.append(piece)

    def pieces(self):
        return self._pieces

    def _append_piece(self, new_piece):
        for piece in self._pieces:
            if piece.end == new_piece.begin:
                piece.append(new_piece)
                return True

    def _prepend_piece(self, new_piece):
        for piece in self._pieces:
            if piece.begin == new_piece.end:
                piece.prepend(new_piece)
                return True

