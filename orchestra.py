import time
import subprocess
from tr_log_reader import TrLogReader
import random
import sys
import os
import re
import liblo
import threading
from synth_controller import SynthController
from osc_sender import OscSender

PORT = 51233
VISUALIZER_PORT = 51234

class Player:
    def __init__(self, orchestra, _id, bearing):
        self.orchestra = orchestra
        self.logger = orchestra.logger
        self.id = _id
        self.bearing = bearing
        self.enabled = True
        self._previous_chunk_time = None
        self._sound = None
        self._cursor = None
        self.synth_player = orchestra.synth.player()

    def dispatch(self, chunk, desired_time):
        chunk["desired_time"] = desired_time
        self.orchestra.visualize(chunk,
                                 self.id,
                                 self.bearing)

    def play(self, chunk, pan, desired_time=None):
        if not desired_time:
            if "desired_time" in chunk:
                desired_time = chunk["desired_time"]
        chunk["pan"] = pan
        if self.interpret_sonically(chunk, desired_time):
            self.orchestra.highlight_chunk(chunk)
        else:
            self.orchestra.stopped_playing(chunk)

    def interpret_sonically(self, chunk, desired_time):
        if self._cursor == (chunk["filenum"], chunk["begin"]):
            desired_duration = desired_time - self._previous_chunk_time
            self.orchestra.logger.debug("desired_duration=%s-%s=%s" % (desired_time, self._previous_chunk_time, desired_duration))
            if desired_duration == 0:
                warn(self.logger, "simultaneous chunks within a peer?")
                desired_duration = 0.01
            self._sound.play_to(
                self._relative_position(chunk), desired_duration,
                self.orchestra.stopped_playing, [chunk])
        else:
            if self._sound:
                self._sound.stop_playing()
            self._sound = self._start_sound(chunk)
        self._cursor = (chunk["filenum"], chunk["end"])
        self._previous_chunk_time = desired_time
        return True

    def _start_sound(self, chunk):
        return self.synth_player.start_playing(
            chunk["filenum"], self._relative_position(chunk), chunk["pan"],
            self.orchestra.stopped_playing, [chunk])

    def _relative_position(self, chunk):
        file_info = self.orchestra.tr_log.files[chunk["filenum"]]
        start_time_in_file = self._bytecount_to_secs(
            chunk["begin"]-file_info["offset"], file_info)
        return start_time_in_file / file_info["duration"]

    def _bytecount_to_secs(self, byte_count, file_info):
        duration_secs = file_info["duration"]
        file_num_bytes = file_info["length"]
        return duration_secs * byte_count / file_num_bytes

    def _play_chunk(self, chunk, desired_time):
        file_info = self.orchestra.tr_log.files[chunk["filenum"]]
        filename = file_info["decoded_name"]
        start_time_in_file = self._bytecount_to_secs(chunk["begin"]-file_info["offset"], file_info)
        end_time_in_file = self._bytecount_to_secs(chunk["end"]-file_info["offset"], file_info)

        if desired_time == None:
            raise Exception("why does this happen?")

        rate = (end_time_in_file - start_time_in_file) / desired_duration
        if rate < Orchestra.MIN_GRAIN_RATE:
            self.logger.debug("skipping chunk due to slow rate %f (probably caused by long pause)", rate)
            self._previous_chunk_time = desired_time
            return False

        self.logger.debug("at %f, playing %s at position %fs with duration %fs, rate %f" % (
                desired_time, filename, start_time_in_file, desired_duration, rate))

        chunk["start_time_in_file"] = start_time_in_file
        chunk["end_time_in_file"] = end_time_in_file
        chunk["desired_duration"] = desired_duration
        self.orchestra.play_chunk(chunk)
        return True


class Orchestra:
    SAMPLE_RATE = 44100
    MIN_GRAIN_RATE = 0.01
    PLAYABLE_FORMATS = ['mp3', 'flac', 'wav', 'm4b']

    _extension_re = re.compile('\.(\w+)$')

    def __init__(self, sessiondir, logger, tr_log,
                 realtime=False,
                 timefactor=1,
                 start_time=0,
                 quiet=False,
                 predecoded=False,
                 file_location=None,
                 visualizer_enabled=False,
                 loop=False,
                 osc_log=None):
        self.sessiondir = sessiondir
        self.logger = logger
        self.tr_log = tr_log
        self.realtime = realtime
        self.timefactor = timefactor
        self.quiet = quiet
        self.predecoded = predecoded
        self.file_location = file_location
        self._loop = loop

        self.gui = None
        self._check_which_files_are_audio()
        self.synth = SynthController(self.logger)
        self._prepare_players()
        self.stopwatch = Stopwatch()
        self.tr_log.flatten() # TODO: find better place for this call
        self.chunks = tr_log.chunks
        self.chunks_by_id = {}
        self._playing = False
        self._quitting = False
        self.set_time_cursor(start_time)

        if visualizer_enabled:
            self.visualizer = OscSender(VISUALIZER_PORT, osc_log)
            self._setup_osc()
        else:
            self.visualizer = None

    def _setup_osc(self):
        self.server = liblo.Server(PORT)
        self.server.add_method("/play", "if", self._handle_play_message)
        server_thread = threading.Thread(target=self._serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def _serve_osc(self):
        while True:
            self.server.recv(0.01)
            time.sleep(0.01)

    def _handle_play_message(self, path, args, types, src, data):
        (chunk_id, pan) = args
        chunk = self.chunks_by_id[chunk_id]
        self.logger.debug("playing chunk %s with pan %s" % (chunk, pan))
        chunk["player"].play(chunk, pan)

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

    def _prepare_players(self):
        self._player_class = Player
        if self.predecoded:
            self._get_wav_files_info()
        else:
            raise Exception("playing wav without precoding is not supported")
        self.players = []
        self._player_for_peer = dict()

    def _get_wav_files_info(self):
        for file_id in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[file_id]
            if "decoded_name" in file_info:
                file_info["duration"] = self._get_file_duration(file_info)
                file_info["num_channels"] = self._get_num_channels(file_info)
                self.logger.debug("duration for %r: %r\n" %
                                  (file_info["name"], file_info["duration"]))
                self.synth.load_sound(file_id, file_info["decoded_name"])

    def _get_file_duration(self, file_info):
        if "decoded_name" in file_info:
            cmd = 'soxi -D "%s"' % file_info["decoded_name"]
            stdoutdata, stderrdata = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE).communicate()
            return float(stdoutdata)

    def _get_num_channels(self, file_info):
        if "decoded_name" in file_info:
            cmd = 'soxi -c "%s"' % file_info["decoded_name"]
            stdoutdata, stderrdata = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE).communicate()
            return int(stdoutdata)

    def get_current_log_time(self):
        return self.log_time_played_from + self.stopwatch.get_elapsed_time() * self.timefactor

    def play_non_realtime(self):
        self.logger.debug("entering play_non_realtime")
        if self._loop:
            while True:
                self._play_until_end()
                self.set_time_cursor(0)
        else:
            self._play_until_end()
            self._quitting = True
        self.logger.debug("leaving play_non_realtime")

    def _play_until_end(self):
        self.logger.debug("entering _play_until_end")
        self._playing = True
        self.stopwatch.start()
        num_chunks = len(self.chunks)
        while self._playing and self.current_chunk_index < num_chunks:
            self.logger.debug("chunk index is %d" % self.current_chunk_index)
            chunk = self.chunks[self.current_chunk_index]
            self.handle_chunk(chunk)
            self.current_chunk_index += 1
        self.logger.debug("leaving _play_until_end")

    def scrub_to_time(self, target_log_time):
        self.logger.debug("scrub_to_time(%s)" % target_log_time)
        if target_log_time > self.get_current_log_time():
            self._scrub_forward_to(target_log_time)
        else:
            self._scrub_backward_to(target_log_time)
        self.set_time_cursor(target_log_time)
        self.logger.debug("scrub_to_time(%s) complete" % target_log_time)

    def _scrub_forward_to(self, target_log_time):
        reached_target = False
        num_chunks = len(self.chunks)
        while not reached_target:
            chunk = self.chunks[self.current_chunk_index]
            if chunk["t"] >= target_log_time:
                reached_target = True
            if not reached_target:
                self.current_chunk_index += 1
                if self.current_chunk_index == num_chunks:
                    reached_target = True
        player = self.get_player_for_chunk(chunk)
        player.play(chunk, pan=0.5)

    def _scrub_backward_to(self, target_log_time):
        reached_target = False
        num_chunks = len(self.chunks)
        while not reached_target:
            chunk = self.chunks[self.current_chunk_index]
            if chunk["t"] <= target_log_time:
                reached_target = True
            if not reached_target:
                self.current_chunk_index += 1
                if self.current_chunk_index < 0 or self.current_chunk_index == num_chunks:
                    reached_target = True
        player = self.get_player_for_chunk(chunk)
        player.play(chunk, pan=0.5)
        
    def stop(self):
        self._playing = False
        self.log_time_played_from = self.get_current_log_time()
        self.stopwatch.stop()

    def handle_chunk(self, chunk):
        self.logger.debug("handling chunk %s" % chunk)
        chunk_start_time = chunk["t"]
        if self._chunk_is_audio(chunk):
            file_info = self.tr_log.files[chunk["filenum"]]
            if self._file_was_downloaded(file_info):
                self.dispatch_chunk(chunk, chunk_start_time)
            else:
                self.logger.debug("skipping chunk in non-downloaded file")
        else:
            self.logger.debug("skipping non-audio chunk")

    def _file_was_downloaded(self, file_info):
        return "decoded_name" in file_info

    def _chunk_is_audio(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return file_info["is_audio"]

    def dispatch_chunk(self, chunk, chunk_start_time):
        now = self.get_current_log_time()
        time_margin = chunk_start_time - now
        self.logger.debug("time_margin=%f-%f=%f" % (chunk_start_time, now, time_margin))
        player = self.get_player_for_chunk(chunk)
        self.logger.debug("get_player_for_chunk returned %s" % player)
        if not self.realtime and time_margin > 0:
            sleep_time = time_margin
            self.logger.debug("sleeping %f" % sleep_time)
            time.sleep(sleep_time)
        chunk_size = chunk["end"] - chunk["begin"]
        if player:
            self.logger.debug("player.enabled=%s" % player.enabled)
        if player and player.enabled:
            self.chunks_by_id[chunk["id"]] = chunk
            now = self.get_current_log_time()
            if self.gui:
                player.play(chunk, pan=0.5, desired_time=now)
            else:
                self.logger.debug("dispatching chunk")
                player.dispatch(chunk, now)

    def highlight_chunk(self, chunk):
        if self.gui:
            self.gui.highlight_chunk(chunk)

    def visualize(self, chunk, player_id, bearing):
        if self.visualizer:
            file_info = self.tr_log.files[chunk["filenum"]]
            self.visualizer.send("/chunk",
                                 chunk["id"],
                                 chunk["begin"],
                                 chunk["end"] - chunk["begin"],
                                 chunk["filenum"],
                                 file_info["offset"],
                                 file_info["length"],
                                 player_id,
                                 bearing)

    def stopped_playing(self, chunk):
        self.logger.debug("stopped chunk %s" % chunk)
        if self.gui:
            self.gui.unhighlight_chunk(chunk)
        if self.visualizer:
            self.visualizer.send("/stopped_playing",
                                 chunk["id"], chunk["filenum"])

    def get_player_for_chunk(self, chunk):
        try:
            return chunk["player"]
        except KeyError:
            peer = chunk["peeraddr"]
            peer_player = None
            try:
                peer_player = self._player_for_peer[peer]
            except KeyError:
                peer_player = self._create_player()
                self.players.append(peer_player)
                self._player_for_peer[peer] = peer_player
            chunk["player"] = peer_player
            return peer_player

    def _create_player(self):
        count = len(self.players)
        bearing = random.uniform(0.0, 1.0)
        self.logger.debug("creating player number %d with bearing %f" % (
                count, bearing))
        return self._player_class(self, count, bearing)

    def set_time_cursor(self, log_time):
        assert not self.realtime
        self.logger.debug("setting time cursor at %f" % log_time)
        self.log_time_played_from = log_time
        if self._playing:
            self.stopwatch.restart()
        self.current_chunk_index = self._get_current_chunk_index()
        self.logger.debug("new chunk index is %d" % self.current_chunk_index)

    def _get_current_chunk_index(self):
        index = 0
        next_to_last_index = len(self.chunks) - 2
        while index < next_to_last_index:
            if self.chunks[index+1]["t"] >= self.log_time_played_from:
                return index
            index += 1
        return len(self.chunks) - 1

class Stopwatch:
    def __init__(self):
        self._running = False

    def start(self):
        self._running = True
        self._real_time_started = time.time()

    def stop(self):
        self._running = False

    def restart(self):
        self.start()

    def running(self):
        return self._running

    def get_elapsed_time(self):
        if self.running():
            return time.time() - self._real_time_started
        else:
            return 0

def warn(logger, message):
    logger.debug(message)
    print >> sys.stderr, "WARNING: %s" % message

