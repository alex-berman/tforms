import time
import subprocess
from tr_log_reader import TrLogReader
import random
import sys
import os
import re
from osc_receiver import OscReceiver
import threading
import sched
from logger import logger
from synth_controller import SynthController
from osc_sender import OscSender
from interpret import Interpreter
from stopwatch import Stopwatch

PORT = 51233
VISUALIZER_PORT = 51234
MAX_MEM_SIZE_KB = 1100000
BYTES_PER_SAMPLE = 4

class Player:
    def __init__(self, orchestra, _id):
        self.orchestra = orchestra
        self.id = _id
        self.enabled = True
        self._previous_chunk_time = None

    def visualize(self, chunk):
        self.orchestra.visualize_chunk(chunk, self)

    def play(self, segment, pan):
        segment["pan"] = pan
        self.interpret_sonically(segment)
        self.orchestra.highlight_segment(segment)

    def _bytecount_to_secs(self, byte_count, file_info):
        duration_secs = file_info["duration"]
        file_num_bytes = file_info["length"]
        return duration_secs * byte_count / file_num_bytes




class WavPlayer(Player):
    def interpret_sonically(self, segment):
        file_info = self.orchestra.tr_log.files[segment["filenum"]]
        filename = file_info["decoded_name"]
        start_time_in_file = self._bytecount_to_secs(segment["begin"]-file_info["offset"], file_info)
        end_time_in_file = self._bytecount_to_secs(segment["end"]-file_info["offset"], file_info)

        logger.debug("playing %s at position %fs with duration %fs" % (
                filename, start_time_in_file, segment["duration"]))

        segment["start_time_in_file"] = start_time_in_file
        segment["end_time_in_file"] = end_time_in_file
        self.orchestra.play_segment(segment, self)
        return True


class Orchestra:
    SAMPLE_RATE = 44100
    PLAYABLE_FORMATS = ['mp3', 'flac', 'wav', 'm4b']

    _extension_re = re.compile('\.(\w+)$')

    def __init__(self, sessiondir, tr_log,
                 realtime=False,
                 timefactor=1,
                 start_time=0,
                 quiet=False,
                 predecoded=False,
                 file_location=None,
                 visualizer_enabled=False,
                 loop=False,
                 osc_log=None,
                 max_passivity=None):
        self.sessiondir = sessiondir
        self.tr_log = tr_log
        self.realtime = realtime
        self.timefactor = timefactor
        self.quiet = quiet
        self.predecoded = predecoded
        self.file_location = file_location
        self._visualizer_enabled = visualizer_enabled
        self._loop = loop
        self._max_passivity = max_passivity

        self.playback_enabled = True
        self.fast_forwarding = False
        self._log_time_for_last_handled_event = 0
        self.gui = None
        self._check_which_files_are_audio()
        self.synth = SynthController()
        self._create_players()
        self._prepare_playable_files()
        self.stopwatch = Stopwatch()
        self.chunks = self._filter_playable_chunks(tr_log.chunks)
        self._interpret_chunks_to_score()
        self._chunks_by_id = {}
        self.segments_by_id = {}
        self._playing = False
        self._quitting = False
        self._informed_visualizer_about_torrent = False
        self.set_time_cursor(start_time)
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self._run_scheduler_thread()

        if self._visualizer_enabled:
            self.visualizer = OscSender(VISUALIZER_PORT, osc_log)
            self._setup_osc()
        else:
            self.visualizer = None

    def _interpret_chunks_to_score(self):
        self.score = Interpreter().interpret(self.chunks, self.tr_log.files)
        if self._max_passivity:
            self._reduce_max_passivity_in_score()
        for segment in self.score:
            segment["duration"] /= self.timefactor

    def _reduce_max_passivity_in_score(self):
        previous_onset = None
        reduced_time = 0
        for i in range(len(self.score)):
            if previous_onset is not None:
                if (self.score[i]["onset"] - reduced_time - previous_onset) > self._max_passivity:
                    reduced_time += self.score[i]["onset"] - reduced_time - previous_onset - self._max_passivity
            self.score[i]["onset"] -= reduced_time
            previous_onset = self.score[i]["onset"]

    def _filter_playable_chunks(self, chunks):
        return filter(lambda chunk: (self._chunk_is_playable(chunk)),
                      chunks)


    def _chunk_is_playable(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return "playable_file_index" in file_info

    def _run_scheduler_thread(self):
        self._scheduler_thread = threading.Thread(target=self._process_scheduled_events)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _process_scheduled_events(self):
        while not self._quitting:
            self.scheduler.run()
            time.sleep(0.01)

    def _setup_osc(self):
        self.server = OscReceiver(PORT)
        self.server.add_method("/visualizing", "ii", self._handle_visualizing_message)
        self.server.add_method("/register", "", self._handle_register)
        self._visualized_registered = False
        server_thread = threading.Thread(target=self._serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def _serve_osc(self):
        while True:
            self.server.recv(0.01)
            time.sleep(0.01)

    def _wait_for_visualizer_to_register(self):
        while not self._visualized_registered:
            time.sleep(0.1)

    def _handle_visualizing_message(self, path, args, types, src, data):
        (segment_id, channel) = args
        segment = self.segments_by_id[segment_id]
        logger.debug("visualizing segment %s with channel %s" % (segment, channel))
        self._ask_synth_to_play_segment(segment, channel=channel, pan=None)

    def _ask_synth_to_play_segment(self, segment, channel, pan):
        logger.debug("asking synth to play %s" % segment)
        file_info = self.tr_log.files[segment["filenum"]]
        self.synth.play_segment(
            segment["id"],
            segment["filenum"],
            segment["start_time_in_file"] / file_info["duration"],
            segment["end_time_in_file"] / file_info["duration"],
            segment["duration"],
            channel,
            pan)
        self.scheduler.enter(
            segment["duration"], 1,
            self.stopped_playing, [segment])

    def _handle_register(self, path, args, types, src, data):
        self._visualized_registered = True

    def _check_which_files_are_audio(self):
        for file_info in self.tr_log.files:
            file_info["is_audio"] = self._has_audio_extension(file_info["name"])

    @staticmethod
    def _has_audio_extension(filename):
        return Orchestra._extension(filename) in Orchestra.PLAYABLE_FORMATS

    @staticmethod
    def _extension(filename):
        m = Orchestra._extension_re.search(filename)
        if m:
            return m.group(1).lower()

    def _create_players(self):
        self._player_class = WavPlayer
        self.players = []
        self._player_for_peer = dict()

    def _prepare_playable_files(self):
        if self.predecoded:
            self._get_wav_files_info()
            self._load_sounds()
        else:
            raise Exception("playing wav without precoding is not supported")

    def _load_sounds(self):
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if "playable_file_index" in file_info:
                self.synth.load_sound(filenum, file_info["decoded_name"])

    def _get_wav_files_info(self):
        playable_file_index = 0
        estimated_mem_size = 0
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if "decoded_name" in file_info:
                file_info["duration"] = self._get_file_duration(file_info)
                if file_info["duration"] > 0:
                    file_info["num_channels"] = self._get_num_channels(file_info)
                    file_info["playable_file_index"] = playable_file_index
                    logger.debug("duration for %r: %r\n" %
                                      (file_info["name"], file_info["duration"]))
                    estimated_mem_size += int(file_info["duration"] * self.SAMPLE_RATE) \
                        * file_info["num_channels"] * BYTES_PER_SAMPLE
                    playable_file_index += 1
        self._num_playable_files = playable_file_index

        estimated_mem_size_kb = estimated_mem_size / 1024
        logger.debug("estimated memory usage for sounds: %s kb" % estimated_mem_size_kb)
        if estimated_mem_size_kb > MAX_MEM_SIZE_KB:
            print >>sys.stderr, "WARNING: estimated mem size of %s exceeds max (%s)" % (
                estimated_mem_size_kb, MAX_MEM_SIZE_KB)

    def _get_file_duration(self, file_info):
        if "decoded_name" in file_info:
            cmd = 'soxi -D "%s"' % file_info["decoded_name"]
            try:
                stdoutdata, stderrdata = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
                return float(stdoutdata)
            except:
                logger.debug("failed to get duration for %s" % file_info["decoded_name"])
                return 0

    def _get_num_channels(self, file_info):
        if "decoded_name" in file_info:
            cmd = 'soxi -c "%s"' % file_info["decoded_name"]
            stdoutdata, stderrdata = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE).communicate()
            return int(stdoutdata)

    def get_current_log_time(self):
        if self.fast_forwarding:
            return self._log_time_for_last_handled_event
        else:
            return self.log_time_played_from + self.stopwatch.get_elapsed_time() * self.timefactor

    def play_non_realtime(self, quit_on_end=False):
        logger.debug("entering play_non_realtime")
        if self._visualizer_enabled:
            self._wait_for_visualizer_to_register()
        if self._loop:
            while True:
                self._play_until_end()
                self.set_time_cursor(0)
        else:
            self._play_until_end()
            if quit_on_end:
                self._quitting = True
        logger.debug("leaving play_non_realtime")

    def _play_until_end(self):
        logger.debug("entering _play_until_end")
        self._playing = True
        self.stopwatch.start()
        no_more_events = False
        while self._playing and not no_more_events:
            event = self._get_next_chunk_or_segment()
            if event:
                self._handle_event(event)
            else:
                no_more_events = True
        logger.debug("leaving _play_until_end")

    def _get_next_chunk_or_segment(self):
        logger.debug("chunk index = %d, segment index = %d" % (
                self.current_chunk_index, self.current_segment_index))
        chunk = self._get_next_chunk()
        segment = self._get_next_segment()
        logger.debug("next chunk: %s" % chunk)
        logger.debug("next segment: %s" % segment)
        if chunk and segment:
            return self._choose_nearest_chunk_or_segment(chunk, segment)
        elif chunk:
            return {"type": "chunk",
                    "chunk": chunk}
        elif segment:
            return {"type": "segment",
                    "segment": segment}
        else:
            return None

    def _get_next_chunk(self):
        if self.current_chunk_index < len(self.chunks):
            return self.chunks[self.current_chunk_index]

    def _get_next_segment(self):
        if self.current_segment_index < len(self.score):
            return self.score[self.current_segment_index]

    def _handle_event(self, event):
        if event["type"] == "chunk":
            self.handle_chunk(event["chunk"])
            self.current_chunk_index += 1
        elif event["type"] == "segment":
            self.handle_segment(event["segment"])
            self.current_segment_index += 1
        else:
            raise Exception("unexpected event %s" % event)

    def _choose_nearest_chunk_or_segment(self, chunk, segment):
        if chunk["t"] < segment["onset"]:
            return {"type": "chunk",
                    "chunk": chunk}
        else:
            return {"type": "segment",
                    "segment": segment}
            
    def stop(self):
        self.synth.stop_all()
        self._playing = False
        self.log_time_played_from = self.get_current_log_time()
        self.stopwatch.stop()

    def handle_segment(self, segment):
        logger.debug("handling segment %s" % segment)
        player = self.get_player_for_segment(segment)
        logger.debug("get_player_for_segment returned %s" % player)
        if not self.fast_forwarding:
            now = self.get_current_log_time()
            time_margin = segment["onset"] - now
            logger.debug("time_margin=%f-%f=%f" % (segment["onset"], now, time_margin))
            if not self.realtime and time_margin > 0:
                sleep_time = time_margin
                logger.debug("sleeping %f" % sleep_time)
                time.sleep(sleep_time)
        if player:
            logger.debug("player.enabled=%s" % player.enabled)
        if player and player.enabled:
            player.play(segment, pan=0.5)
        self._log_time_for_last_handled_event = segment["onset"]

    def handle_chunk(self, chunk):
        logger.debug("handling chunk %s" % chunk)
        player = self.get_player_for_chunk(chunk)
        logger.debug("get_player_for_chunk returned %s" % player)
        if not self.fast_forwarding:
            now = self.get_current_log_time()
            time_margin = chunk["t"] - now
            logger.debug("time_margin=%f-%f=%f" % (chunk["t"], now, time_margin))
            if not self.realtime and time_margin > 0:
                sleep_time = time_margin
                logger.debug("sleeping %f" % sleep_time)
                time.sleep(sleep_time)
        if player:
            logger.debug("player.enabled=%s" % player.enabled)
        if player and player.enabled:
            player.visualize(chunk)
        self._log_time_for_last_handled_event = chunk["t"]

    def highlight_segment(self, segment):
        if self.gui:
            self.gui.highlight_segment(segment)

    def visualize_chunk(self, chunk, player):
        if self.visualizer:
            if not self._informed_visualizer_about_torrent:
                self._send_torrent_info_to_visualizer()
            file_info = self.tr_log.files[chunk["filenum"]]
            self._chunks_by_id[chunk["id"]] = chunk
            self.visualizer.send("/chunk",
                                 chunk["id"],
                                 chunk["begin"],
                                 chunk["end"] - chunk["begin"],
                                 file_info["playable_file_index"],
                                 player.id)

    def visualize_segment(self, segment, player):
        if self.visualizer:
            if not self._informed_visualizer_about_torrent:
                self._send_torrent_info_to_visualizer()
            file_info = self.tr_log.files[segment["filenum"]]
            self.segments_by_id[segment["id"]] = segment
            self.visualizer.send("/segment",
                                 segment["id"],
                                 segment["begin"],
                                 segment["end"] - segment["begin"],
                                 file_info["playable_file_index"],
                                 player.id,
                                 segment["duration"])
        else:
            self._ask_synth_to_play_segment(segment, channel=0, pan=0.5)

    def stopped_playing(self, segment):
        logger.debug("stopped segment %s" % segment)
        if self.gui:
            self.gui.unhighlight_segment(segment)

    def play_segment(self, segment, player):
        self.segments_by_id[segment["id"]] = segment
        self.visualize_segment(segment, player)

    def _send_torrent_info_to_visualizer(self):
        self._informed_visualizer_about_torrent = True
        self.visualizer.send("/torrent", self._num_playable_files)
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if "playable_file_index" in file_info:
                self.visualizer.send("/file",
                                     file_info["playable_file_index"],
                                     file_info["offset"],
                                     file_info["length"])

    def get_player_for_chunk(self, chunk):
        try:
            return chunk["player"]
        except KeyError:
            peer_player = self.get_player_for_peer(chunk["peeraddr"])
            chunk["player"] = peer_player
            return peer_player

    def get_player_for_segment(self, segment):
        try:
            return segment["player"]
        except KeyError:
            peer_player = self.get_player_for_peer(segment["peeraddr"])
            segment["player"] = peer_player
            return peer_player

    def get_player_for_peer(self, peeraddr):
        peer_player = None
        try:
            peer_player = self._player_for_peer[peeraddr]
        except KeyError:
            peer_player = self._create_player()
            self.players.append(peer_player)
            self._player_for_peer[peeraddr] = peer_player
        return peer_player

    def _create_player(self):
        count = len(self.players)
        logger.debug("creating player number %d" % count)
        return self._player_class(self, count)

    def set_time_cursor(self, log_time):
        assert not self.realtime
        logger.debug("setting time cursor at %f" % log_time)
        self.log_time_played_from = log_time
        if self._playing:
            self.stopwatch.restart()
        self.current_chunk_index = self._get_current_chunk_index()
        self.current_segment_index = self._get_current_segment_index()

    def _get_current_chunk_index(self):
        index = 0
        next_to_last_index = len(self.chunks) - 2
        while index < next_to_last_index:
            if self.chunks[index+1]["t"] >= self.log_time_played_from:
                return index
            index += 1
        return len(self.chunks) - 1

    def _get_current_segment_index(self):
        index = 0
        next_to_last_index = len(self.score) - 2
        while index < next_to_last_index:
            if self.score[index+1]["onset"] >= self.log_time_played_from:
                return index
            index += 1
        return len(self.score) - 1

    def shutdown(self):
        if self.visualizer:
            self.visualizer.send("/shutdown")

def warn(logger, message):
    logger.debug(message)
    print >> sys.stderr, "WARNING: %s" % message

