import unittest
from gatherer import Gatherer
import os
import sys
import random

dirname = os.path.dirname(__file__)
if dirname:
    sys.path.append(dirname + "/..")
else:
    sys.path.append("..")
from tr_log_reader import TrLogReader
#from interpret import Interpreter

SESSION_FILENAME = "../sessions/120827-084403-TDL4/session.log"

class File:
    def __init__(self, offset, length):
        self.offset = offset
        self.length = length

class Piece:
    def __init__(self, begin, end, f):
        self.begin = begin
        self.end = end
        self.f = f
        self.torrent_begin = self.begin + f.offset
        self.torrent_end = self.end + f.offset

    def __eq__(self, other):
        return self.begin == other.begin and \
            self.end == other.end and \
            self.torrent_begin == other.torrent_begin and \
            self.torrent_end == other.torrent_end

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return 'Piece(begin=%s, end=%s, torrent_begin=%s, torrent_end=%s)' % (
            self.begin, self.end, self.torrent_begin, self.torrent_end)

    def append(self, other):
        self.end = other.end

    def prepend(self, other):
        self.begin = other.begin

    def __hash__(self):
        return hash((self.begin, self.end))

    def joinable_with(self, other):
        return True

class GathererTest(unittest.TestCase):
    def test_expected_order(self):
        for chunk in self.tr_log.chunks:
            self._gather(chunk)
        self.assertEquals(1, len(self.gatherer.pieces()))
        
    def test_random_order(self):
        while len(self.tr_log.chunks) > 0:
            index = random.randint(0, len(self.tr_log.chunks)-1)
            chunk = self.tr_log.chunks[index]
            del self.tr_log.chunks[index]
            self._gather(chunk)
        self.assertEquals(1, len(self.gatherer.pieces()))
        
    def setUp(self):
        self.tr_log = TrLogReader(SESSION_FILENAME).get_log()
        #self.segments = Interpreter().interpret(self.tr_log.chunks, self.tr_log.files)
        self.gatherer = Gatherer()
        self.files = [File(f["offset"], f["length"]) for f in self.tr_log.files]

    def _gather(self, piece_info):
        f = self.files[piece_info["filenum"]]
        begin = piece_info["begin"] - f.offset
        end = piece_info["end"] - f.offset
        self.gatherer.add(Piece(begin, end, f))
