import unittest
from tr_log_reader import TrLogReader, TrLog
import os

FILENAME = "mockup_tr_log.log"
EXPECTED_FILES = [{'length': 291, 'lastpiece': 0, 'firstpiece': 0, 'name': 'The Cataracs-Top of the WorldLike a G6 Remix Single/Distributed by Mininova.txt', 'offset': 0}, {'length': 969, 'lastpiece': 0, 'firstpiece': 0, 'name': 'The Cataracs-Top of the WorldLike a G6 Remix Single/The_Cataracs-Top_of_the_World_BW_Like_A_G6_(Lil_Prophet_Remix_Single)-2010/00-the_cataracs-top_of_the_world_bw_like_a_g6_(remix_single)-2010.m3u', 'offset': 291}]
EXPECTED_CHUNKS = [{'begin': 28311552, 'end': 28312953, 'peeraddr': '221.187.146.133:5465', 'id': 0, 't': 0.0, 'filenum': 0}, {'begin': 28312953, 'end': 28312999, 'peeraddr': '221.187.146.133:5465', 'id': 1, 't': 0.315, 'filenum': 0}]
EXPECTED_PEERS = ['221.187.146.133:5465']
EXPECTED_TOTALSIZE = 28348491

class TrLogReaderTests(unittest.TestCase):
    def test_file_processing_without_cache(self):
        tr_log = TrLogReader(FILENAME).get_log(use_cache=False)
        self.assertEquals(EXPECTED_FILES, tr_log.files)
        self.assertEquals(EXPECTED_CHUNKS, tr_log.chunks)
        self.assertEquals(EXPECTED_PEERS, tr_log.peers)
        self.assertEquals(EXPECTED_TOTALSIZE, tr_log.totalsize)

    def test_loading_from_cache(self):
        TrLogReader(FILENAME).get_log(use_cache=True)
        self.assertTrue(os.path.exists(FILENAME + ".cache"))
        tr_log_from_cache = TrLogReader(FILENAME).get_log(use_cache=True)
        self.assertEquals(EXPECTED_FILES, tr_log_from_cache.files)
        self.assertEquals(EXPECTED_CHUNKS, tr_log_from_cache.chunks)
        self.assertEquals(EXPECTED_PEERS, tr_log_from_cache.peers)
        self.assertEquals(EXPECTED_TOTALSIZE, tr_log_from_cache.totalsize)

class TrLogTests(unittest.TestCase):
    def test_flatten(self):
        unflattened_chunks = [
            {'filenum': 0, 'begin': 100, 'end': 200, 't': 0.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 300, 'end': 400, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 400, 'end': 500, 't': 20.0, 'peeraddr': 'A'}
            ]
        expected_result = [
            {'filenum': 0, 'begin': 100, 'end': 200, 't': 0.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 200, 'end': 400, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 400, 'end': 500, 't': 20.0, 'peeraddr': 'A'}
            ]
        log = TrLog()
        log.chunks = unflattened_chunks
        log.flatten()
        self.assertEquals(expected_result, log.chunks)

    def test_flatten_considers_peer(self):
        unflattened_chunks = [
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 300, 'end': 400, 't': 10.0, 'peeraddr': 'B'}
            ]
        expected_result = unflattened_chunks
        log = TrLog()
        log.chunks = unflattened_chunks
        log.flatten()
        self.assertEquals(expected_result, log.chunks)

    def test_flatten_considers_files(self):
        unflattened_chunks = [
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 1, 'begin': 300, 'end': 400, 't': 10.0, 'peeraddr': 'A'}
            ]
        expected_result = unflattened_chunks
        log = TrLog()
        log.chunks = unflattened_chunks
        log.flatten()
        self.assertEquals(expected_result, log.chunks)

    def test_flatten_handles_interwoven_peers(self):
        unflattened_chunks = [
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 500, 'end': 600, 't': 10.0, 'peeraddr': 'B'},
            {'filenum': 0, 'begin': 300, 'end': 400, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 600, 'end': 700, 't': 10.0, 'peeraddr': 'B'},
            ]
        expected_result = [
            {'filenum': 0, 'begin': 200, 'end': 400, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 500, 'end': 700, 't': 10.0, 'peeraddr': 'B'},
            ]
        log = TrLog()
        log.chunks = unflattened_chunks
        log.flatten()
        self.assertEquals(expected_result, log.chunks)

    def test_flatten_considers_end_and_begin(self):
        unflattened_chunks = [
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 10.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 305, 'end': 400, 't': 10.0, 'peeraddr': 'A'}
            ]
        expected_result = unflattened_chunks
        log = TrLog()
        log.chunks = unflattened_chunks
        log.flatten()
        self.assertEquals(expected_result, log.chunks)
