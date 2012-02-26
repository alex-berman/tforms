import re
import sys
import os
import Queue
import cPickle

class TrLog:
    def lastchunktime(self):
        return self.chunks[-1]["t"]

    def lastchunklength(self):
        return self.chunks[-1]["end"] - self.chunks[-1]["begin"]

    def averagechunklength(self):
        return sum(map(lambda x: x["end"] - x["begin"], self.chunks)) / len(self.chunks)

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
        cPickle.dump(self.totalsize, f)
        f.close()

    @staticmethod
    def from_cache(filename):
        log = TrLog()
        f = open(filename, 'r')
        log.files = cPickle.load(f)
        log.chunks = cPickle.load(f)
        log.peers = cPickle.load(f)
        log.totalsize = cPickle.load(f)
        f.close()
        return log

    def flatten(self):
        result = []
        peer_cursor = {}
        for chunk in self.chunks:
            if chunk['peeraddr'] in peer_cursor:
                previous_chunk = peer_cursor[chunk['peeraddr']]
                if previous_chunk['t'] == chunk['t'] \
                        and previous_chunk['end'] == chunk['begin']:
                    previous_chunk['end'] = chunk['end']
                else:
                    result.append(chunk)
                    peer_cursor[chunk['peeraddr']] = chunk
            else:
                result.append(chunk)
                peer_cursor[chunk['peeraddr']] = chunk
        self.chunks = result


class TrLogReader:
    NO_MORE_CHUNKS = {}

    def __init__(self, logfilename, torrent_name="",
                 logger=None, realtime=False, pretend_sequential=False):
        self.logfilename = logfilename
        self.torrent_name = torrent_name
        self.logger = logger
        self.realtime = realtime
        self.pretend_sequential = pretend_sequential
        if self.realtime:
            self.chunks_queue = Queue.Queue()
        self.id = None
        self.files = []
        self.peers = []

    def get_log(self, use_cache=True):
        if use_cache and os.path.exists(self._cache_filename()):
            return TrLog.from_cache(self._cache_filename())
        else:
            self.logfile = open(self.logfilename, "r")
            self._process_torrent_info()
            self._process_chunks()
            self.logfile.close()
            log = TrLog()
            log.files = self.files
            log.chunks = self.chunks
            log.peers = self.peers
            log.totalsize = self.totalsize
            if use_cache:
                self._cache_log(log)
            return log

    def _cache_log(self, log):
        log.save_cache(self._cache_filename())

    def _cache_filename(self):
        return self.logfilename + '.cache'

    def _process_torrent_info(self):
        self._process_until_selected_torrent()
        self._process_files_info()

    def _process_until_selected_torrent(self):
        self.debug("selecting torrent")
        initialized_re = re.compile('initialized torrent (\d+): name=(.*) totalSize=(\d+) fileCount=(\d+) pieceSize=(\d+) pieceCount=(\d+)')
        for line in self.logfile:
            line = line.rstrip("\r\n")
            self.debug("processing: %s" % line)
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
            self.debug("no torrent found")
            raise Exception("no torrent found")
        self.debug("selected torrent '%s' (TID=%d totalsize=%d piecesize=%d)" % \
            (self.name, self.id, self.totalsize, self.piecesize))

    def _process_files_info(self):
        if not self.realtime:
            self.logfile.seek(0)
        file_info_re = re.compile('^TID=%d file=(\d+) offset=(\d+) length=(\d+) firstPiece=(\d+) lastPiece=(\d+) name=(.*)$' % self.id)
        self.debug("starting to search for file info in log")
        for line in self.logfile:
            line = line.rstrip("\r\n")
            self.debug("processing: %s" % line)
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
        chunk_re = re.compile('^\[(\d+)\] chunkId=(\d+) TID=%d peer=([0-9.:]+) got (\d+) bytes for block (\d+) at offset (\d+) in file (\d+) at offset (\d+) \.\.\. remaining (\d+) of (\d+)$' % self.id)
        self.filenummax = 0
        if not self.realtime:
            self.chunks = []
        self.debug("starting to search for chunk info in log")
        for line in self.logfile:
            line = line.rstrip("\r\n")
            self.debug("processing: %s" % line)
            m = chunk_re.search(line)
            if m:
                self._process_chunk_line(m)
        if self.realtime:
            self.chunks_queue.put_nowait(self.NO_MORE_CHUNKS)
        elif self.pretend_sequential:
            self.chunks = self.sort_chunks_sequentially(self.chunks)

    def _process_chunk_line(self, m):
        (t,chunk_id,peeraddr,nbytes,blockindex,blockoffset,filenum,fileoffset,remain,blocksize) = m.groups()
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
        chunk = {"id": int(chunk_id),
                 "t": t,
                 "begin": b1,
                 "end": b2,
                 "peeraddr": peeraddr,
                 "filenum": filenum}
        self._add_peer_unless_already_added(peeraddr)
        self._add_chunk(chunk)

    def _add_peer_unless_already_added(self, peeraddr):
        if peeraddr not in self.peers:
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
        if self.realtime:
            self.chunks_queue.put_nowait(chunk)
        else:
            self.chunks.append(chunk)

    def debug(self, msg):
        if self.logger:
            self.logger.debug(msg)
