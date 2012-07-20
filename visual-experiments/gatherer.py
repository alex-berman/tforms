class Gatherer:
    def __init__(self):
        self._pieces = []

    def add(self, new_piece):
        appendable_piece = self._find_appendable_piece(new_piece)
        if appendable_piece:
            appendable_piece.append(new_piece)
        else:
            prependable_piece = self._find_prependable_piece(new_piece)
            if prependable_piece:
                prependable_piece.prepend(new_piece)
            else:
                self._pieces.append(new_piece)

    def pieces(self):
        return self._pieces

    def _find_appendable_piece(self, new_piece):
        for piece in self._pieces:
            if piece.end == new_piece.begin:
                return piece

    def _find_prependable_piece(self, new_piece):
        for piece in self._pieces:
            if piece.begin == new_piece.end:
                return piece
