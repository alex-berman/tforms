import unittest
from tr_log_reader import TrLogReader, TrLog
import os

FILENAME = "mockup_tr_log.log"
EXPECTED_FILES = [{'length': 291, 'lastpiece': 0, 'firstpiece': 0, 'name': 'The Cataracs-Top of the WorldLike a G6 Remix Single/Distributed by Mininova.txt', 'offset': 0}, {'length': 969, 'lastpiece': 0, 'firstpiece': 0, 'name': 'The Cataracs-Top of the WorldLike a G6 Remix Single/The_Cataracs-Top_of_the_World_BW_Like_A_G6_(Lil_Prophet_Remix_Single)-2010/00-the_cataracs-top_of_the_world_bw_like_a_g6_(remix_single)-2010.m3u', 'offset': 291}]
EXPECTED_CHUNKS = [{'begin': 0, 'end': 100, 'peeraddr': '221.187.146.133', 'id': 0, 't': 0.0, 'filenum': 0}, {'begin': 100, 'end': 184, 'peeraddr': '221.187.146.133', 'id': 1, 't': 0.315, 'filenum': 0}]
EXPECTED_PEERS = ['221.187.146.133']
EXPECTED_TOTALSIZE = 28348491

class TrLogReaderTests(unittest.TestCase):
    def test_file_processing_without_cache(self):
        tr_log = TrLogReader(FILENAME).get_log(use_cache=False, ignore_non_downloaded_files=False)
        self.assertEquals(EXPECTED_FILES, tr_log.files)
        self.assertEquals(EXPECTED_CHUNKS, tr_log.chunks)
        self.assertEquals(EXPECTED_PEERS, tr_log.peers)
        self.assertEquals(EXPECTED_TOTALSIZE, tr_log.totalsize)

    def test_loading_from_cache(self):
        TrLogReader(FILENAME).get_log(use_cache=True, ignore_non_downloaded_files=False)
        expected_cache_filename = FILENAME + ".cache"
        self.assertTrue(os.path.exists(FILENAME + ".cache"))
        tr_log_from_cache = TrLogReader(FILENAME).get_log(use_cache=True)
        os.remove(expected_cache_filename)
        self.assertEquals(EXPECTED_FILES, tr_log_from_cache.files)
        self.assertEquals(EXPECTED_CHUNKS, tr_log_from_cache.chunks)
        self.assertEquals(EXPECTED_PEERS, tr_log_from_cache.peers)
        self.assertEquals(EXPECTED_TOTALSIZE, tr_log_from_cache.totalsize)

    def test_chunk_overlapping_multiple_files(self):
        reader = TrLogReader(FILENAME)
        tr_log = reader.get_log(use_cache=False, ignore_non_downloaded_files=False)
        reader._chunk_count = 0
        chunk = {'filenum': 0,
                 'begin': 0, 'end': 300,
                 'peeraddr': 'X', 'id': 0, 't': 0.0}
        expected_chunks = [
            {'filenum': 0,
             'begin': 0, 'end': 291,
             'peeraddr': 'X', 'id': 0, 't': 0.0},
            {'filenum': 1,
             'begin': 291, 'end': 300,
             'peeraddr': 'X', 'id': 1, 't': 0.0}]
        self.assertEquals(expected_chunks, reader._split_chunk_at_file_boundaries(chunk))

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

    def test_ignore_non_downloaded_files(self):
        log = TrLog()
        log.files = [
            {'offset': 0,    'length': 1000, 'exists_on_disk': False},
            {'offset': 1000, 'length': 1000, 'exists_on_disk': True},
            {'offset': 2000, 'length': 1000, 'exists_on_disk': False},
            {'offset': 3000, 'length': 1000, 'exists_on_disk': True}, # no chunks in log
            {'offset': 4000, 'length': 1000, 'exists_on_disk': True},
            ]
        log.chunks = [
            {'filenum': 0, 'begin': 500, 'end': 600},
            {'filenum': 1, 'begin': 1200, 'end': 1300},
            {'filenum': 1, 'begin': 1400, 'end': 1500},
            {'filenum': 4, 'begin': 4200, 'end': 4300},
            {'filenum': 4, 'begin': 4400, 'end': 4500},
            {'filenum': 2, 'begin': 2500, 'end': 2600},
            ]
        expected_result = [
            {'filenum': 0, 'begin':  200, 'end':  300},
            {'filenum': 0, 'begin':  400, 'end':  500},
            {'filenum': 1, 'begin': 1200, 'end': 1300},
            {'filenum': 1, 'begin': 1400, 'end': 1500}
            ]
        def exists(f):
            return f['exists_on_disk']
        log._file_exists = exists
        log._ignore_non_downloaded_files()
        self.assertEquals(expected_result, log.chunks)
        self.assertEquals(2000, log.total_file_size())

    def test_reduce_max_passivity(self):
        non_reduced_chunks = [
            {'filenum': 0, 'begin': 100, 'end': 200, 't': 0.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 1.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 300, 'end': 400, 't': 20.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 400, 'end': 500, 't': 22.0, 'peeraddr': 'A'}
            ]
        expected_result = [
            {'filenum': 0, 'begin': 100, 'end': 200, 't': 0.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 200, 'end': 300, 't': 1.0, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 300, 'end': 400, 't': 2.5, 'peeraddr': 'A'},
            {'filenum': 0, 'begin': 400, 'end': 500, 't': 4.0, 'peeraddr': 'A'}
            ]
        log = TrLog()
        actual_result = log._reduce_max_passivity(non_reduced_chunks, 1.5)
        self.assertEquals(expected_result, actual_result)

    def test_select_files(self):
        log = TrLog()
        log.files = [
            {'offset': 0,    'length': 1000},
            {'offset': 1000, 'length': 2000}, # selected
            {'offset': 3000, 'length': 3000},
            {'offset': 6000, 'length': 4000}, # selected
            ]
        log.chunks = [
            {'filenum': 1, 'begin': 1200, 'end': 1300},
            {'filenum': 1, 'begin': 1400, 'end': 1500},
            {'filenum': 2, 'begin': 3200, 'end': 3300},
            {'filenum': 3, 'begin': 6200, 'end': 6300},
            {'filenum': 3, 'begin': 6400, 'end': 6500},
            ]

        log.select_files([1, 3])
        expected_files = [
            {'offset': 0,    'length': 2000},
            {'offset': 2000, 'length': 4000},
            ]
        expected_chunks = [
            {'filenum': 0, 'begin': 200, 'end': 300},
            {'filenum': 0, 'begin': 400, 'end': 500},
            {'filenum': 1, 'begin': 2200, 'end': 2300},
            {'filenum': 1, 'begin': 2400, 'end': 2500},
            ]
        self.assertEquals(expected_files, log.files)
        self.assertEquals(expected_chunks, log.chunks)
        self.assertEquals(6000, log.total_file_size())
