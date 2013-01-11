import re
import sys
import os
import Queue
import cPickle
import copy
from logger import logger
from config import DOWNLOAD_LOCATION

_peeraddr_re = re.compile('^\[?([0-9.]+)\]?:')

class TrLog:
    CACHE_VERSION = 0.3

    def lastchunktime(self):
        return self.chunks[-1]["t"]

    def lastchunklength(self):
        return self.chunks[-1]["end"] - self.chunks[-1]["begin"]

    def averagechunklength(self):
        return sum(map(lambda x: x["end"] - x["begin"], self.chunks)) / len(self.chunks)

    def total_file_size(self):
        return sum([f["length"] for f in self.files])

    @staticmethod
    def sort_chunks_sequentially(chunks):
        times = map(lambda x: x["t"], chunks)
        sorted_chunks = sorted(chunks, lambda x,y: cmp(x["begin"], y["begin"]))
        result = []
        i = 0
        for chunk in sorted_chunks:
            chunk["t"] = times[i]
            result.append(chunk)
            i += 1
        return result

    def save_cache(self, filename):
        f = open(filename, 'w')
        cPickle.dump(self.files, f)
        cPickle.dump(self.chunks, f)
        cPickle.dump(self.peers, f)
        cPickle.dump(self.peeraddr_to_id, f)
        cPickle.dump(self.totalsize, f)
        cPickle.dump(self.CACHE_VERSION, f)
        cPickle.dump(self.chunks_reduced_passivity, f)
        f.close()

    @staticmethod
    def from_cache(filename):
        log = TrLog()
        f = open(filename, 'r')
        log.files = cPickle.load(f)
        log.chunks = cPickle.load(f)
        log.peers = cPickle.load(f)
        log.peeraddr_to_id = cPickle.load(f)
        log.totalsize = cPickle.load(f)
        try:
            actual_cache_version = cPickle.load(f)
            if actual_cache_version != TrLog.CACHE_VERSION:
                raise Exception("Session cache of unsupported version (expected %s, found %s). Try to delete the cache file (%s) manually and then retry what you just attempted." % (
                        TrLog.CACHE_VERSION, actual_cache_version, filename))
            log.chunks_reduced_passivity = cPickle.load(f)
        except EOFError:
            raise Exception("Failed to read session cache. The cache file (%s) is probably depcrecated. Try to delete cache file manually and then retry what you just attempted." % filename)
        f.close()
        return log

    def flatten(self):
        result = []
        peer_cursor = {}
        for chunk in self.chunks:
            if chunk['peeraddr'] in peer_cursor:
                previous_chunk = peer_cursor[chunk['peeraddr']]
                if (previous_chunk['t'] == chunk['t']
                    and previous_chunk['filenum'] == chunk['filenum']
                    and previous_chunk['end'] == chunk['begin']):
                    previous_chunk['end'] = chunk['end']
                else:
                    result.append(chunk)
                    peer_cursor[chunk['peeraddr']] = chunk
            else:
                result.append(chunk)
                peer_cursor[chunk['peeraddr']] = chunk
        self.chunks = result

    def _ignore_non_downloaded_files(self):
        for filenum in reversed(range(len(self.files))):
            f = self.files[filenum]
            if not (self._file_exists(f) and self._has_chunks_in_log(filenum)):
                self._remove_file(filenum)

    def _file_exists(self, f):
        return os.path.exists("%s/%s" % (DOWNLOAD_LOCATION, f["name"]))

    def _has_chunks_in_log(self, filenum):
        for chunk in self.chunks:
            if chunk["filenum"] == filenum:
                return True

    def select_files(self, selected_filenums):
        for filenum in reversed(range(len(self.files))):
            if filenum not in selected_filenums:
                self._remove_file(filenum)

    def _remove_file(self, filenum):
        f = self.files[filenum]
        file_begin = f["offset"]
        file_length = f["length"]
        file_end = file_begin + file_length
        chunks_to_delete = []
        for index in range(len(self.chunks)):
            chunk = self.chunks[index]
            if chunk["filenum"] == filenum:
                chunks_to_delete.append(index)
            elif chunk["filenum"] > filenum:
                chunk["begin"] -= file_length
                chunk["end"] -= file_length
                chunk["filenum"] -= 1
        for index in reversed(chunks_to_delete):
            del self.chunks[index]

        for index in range(filenum+1, len(self.files)):
            f = self.files[index]
            f["offset"] -= file_length
        del self.files[filenum]

    def _reduce_max_passivity(self, chunks, max_passivity):
        previous_t = 0
        reduced_time = 0
        result = copy.deepcopy(chunks)
        for i in range(len(result)):
            if (result[i]["t"] - reduced_time - previous_t) > max_passivity:
                reduced_time += result[i]["t"] - reduced_time - previous_t - max_passivity
            result[i]["t"] -= reduced_time
            previous_t = result[i]["t"]
        return result

class TrLogReader:
    NO_MORE_CHUNKS = {}

    def __init__(self, logfilename, torrent_name="",
                 realtime=False, pretend_sequential=False):
        self.logfilename = logfilename
        self.torrent_name = torrent_name
        self.realtime = realtime
        self.pretend_sequential = pretend_sequential
        if self.realtime:
            self.chunks_queue = Queue.Queue()
        self.id = None
        self.files = []
        self.peers = []
        self.peeraddr_to_id = {}
        self._chunk_count = 0

    def get_log(self,
                use_cache=True,
                ignore_non_downloaded_files=True,
                max_passivity=1.0,
                reduced_passivity=False):
        if use_cache and os.path.exists(self._cache_filename()):
            log = TrLog.from_cache(self._cache_filename())
        else:
            self.logfile = open(self.logfilename, "r")
            self._process_torrent_info()
            self._process_chunks()
            self.logfile.close()
            log = TrLog()
            log.files = self.files
            log.chunks = self.chunks
            log.peers = self.peers
            log.peeraddr_to_id = self.peeraddr_to_id
            log.totalsize = self.totalsize
            if ignore_non_downloaded_files:
                log._ignore_non_downloaded_files()
            if max_passivity:
                log.chunks_reduced_passivity = log._reduce_max_passivity(self.chunks, max_passivity)
            if use_cache:
                self._cache_log(log)
        if reduced_passivity:
            log.chunks = log.chunks_reduced_passivity
        return log

    def _cache_log(self, log):
        log.save_cache(self._cache_filename())

    def _cache_filename(self):
        return self.logfilename + '.cache'

    def _process_torrent_info(self):
        self._process_until_selected_torrent()
        self._process_files_info()

    def _process_until_selected_torrent(self):
        logger.debug("selecting torrent")
        initialized_re = re.compile('initialized torrent (\d+): name=(.*) totalSize=(\d+) fileCount=(\d+) pieceSize=(\d+) pieceCount=(\d+)')
        for line in self.logfile:
            line = line.rstrip("\r\n")
            logger.debug("processing: %s" % line)
            m = initialized_re.search(line)
            if m:
                (id,name,totalsize,filecount,piecesize,piececount) = m.groups()
                if self.torrent_name == "" or re.search(self.torrent_name, name):
                    self.id = int(id)
                    self.name = name
                    self.totalsize = int(totalsize)
                    self.numfiles = int(filecount)
                    self.piecesize = int(piecesize)
                    break
        if self.id == None:
            logger.debug("no torrent found")
            raise Exception("no torrent found")
        logger.debug("selected torrent '%s' (TID=%d totalsize=%d piecesize=%d)" % \
            (self.name, self.id, self.totalsize, self.piecesize))

    def _process_files_info(self):
        if not self.realtime:
            self.logfile.seek(0)
        file_info_re = re.compile('^TID=%d file=(\d+) offset=(\d+) length=(\d+) firstPiece=(\d+) lastPiece=(\d+) name=(.*)$' % self.id)
        logger.debug("starting to search for file info in log")
        for line in self.logfile:
            line = line.rstrip("\r\n")
            logger.debug("processing: %s" % line)
            m = file_info_re.search(line)
            if m:
                self._process_file_info_line(m)
                if len(self.files) == self.numfiles:
                    return
        raise Exception("failed to find file info about all %d files (only found %d)" % (
                self.numfiles, len(self.files)))

    def _process_chunks(self):
        self.numdata = 0
        self.time_offset = None
        self._chunk_re = re.compile('^\[(\d+)\] TID=%d peer=([^ ]+) got (\d+) bytes for block (\d+) at offset (\d+) in file (\d+) at offset (\d+) \.\.\. remaining (\d+) of (\d+)$' % self.id)
        self.filenummax = 0
        if not self.realtime:
            self.chunks = []
        logger.debug("starting to search for chunk info in log")
        for line in self.logfile:
            line = line.rstrip("\r\n")
            logger.debug("processing: %s" % line)
            self._process_chunk_line(line)
        if self.realtime:
            self.chunks_queue.put_nowait(self.NO_MORE_CHUNKS)
        elif self.pretend_sequential:
            self.chunks = self.sort_chunks_sequentially(self.chunks)

    def _process_chunk_line(self, line):
        chunk = self._parse_chunk_line(line)
        if chunk:
            chunks = self._split_chunk_at_file_boundaries(chunk)
            for chunk in chunks:
                self._add_chunk(chunk)

    def _split_chunk_at_file_boundaries(self, chunk):
        result = []
        filenum = 0
        for f in self.files:
            if self._chunk_matches_file(chunk, f):
                new_chunk = copy.copy(chunk)
                new_chunk["id"] = self._next_chunk_id()
                new_chunk["filenum"] = filenum
                new_chunk["begin"] = max(chunk["begin"], f["offset"])
                new_chunk["end"] = min(chunk["end"], f["offset"] + f["length"])
                result.append(new_chunk)
            filenum += 1
        return result

    def _chunk_matches_file(self, chunk, f):
        return (f["offset"] <= chunk["begin"] < (f["offset"] + f["length"]) or
                f["offset"] < chunk["end"] < (f["offset"] + f["length"]))

    def _next_chunk_id(self):
        result = self._chunk_count
        self._chunk_count += 1
        return result

    def _parse_chunk_line(self, line):
        m = self._chunk_re.search(line)
        if not m:
            return None
        (t,peeraddr,nbytes,blockindex,blockoffset,filenum,fileoffset,remain,blocksize) = m.groups()
        filenum = int(filenum)
        self.filenummax = max(self.filenummax, filenum)
        t = int(t)
        if self.time_offset == None:
            self.time_offset = t
        t = float(t - self.time_offset) / 1000
        nbytes = int(nbytes)
        blockindex = int(blockindex)
        blockoffset = int(blockoffset)
        remain = int(remain)
        blocksize = int(blocksize)
        b1 = (blockoffset+blocksize-remain-nbytes) + (blockindex*self.piecesize)
        b2 = b1 + nbytes
        chunk = {"t": t,
                 "begin": b1,
                 "end": b2,
                 "peeraddr": self._parse_peeraddr(peeraddr),
                 "filenum": filenum}
        return chunk

    def _parse_peeraddr(self, string):
        m = _peeraddr_re.search(string)
        if m:
            return m.group(1)
        else:
            return string

    def _add_peer_unless_already_added(self, peeraddr):
        if peeraddr not in self.peeraddr_to_id:
            self.peeraddr_to_id[peeraddr] = len(self.peers)
            self.peers.append(peeraddr)

    def _process_file_info_line(self, m):
        (file_id,offset,length,firstpiece,lastpiece,name) = m.groups()
        file_id = int(file_id)
        info = {"offset": int(offset),
                "length": int(length),
                "firstpiece": int(firstpiece),
                "lastpiece": int(lastpiece),
                "name": name}
        self.files.insert(file_id, info)

    def _add_chunk(self, chunk):
        self._add_peer_unless_already_added(chunk["peeraddr"])
        if self.realtime:
            self.chunks_queue.put_nowait(chunk)
        else:
            self.chunks.append(chunk)
