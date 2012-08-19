import time
import subprocess
from tr_log_reader import TrLogReader
import random
import sys
import os
import re
import liblo
import threading
import sched
from synth_controller import SynthController
from osc_sender import OscSender
from interpret import Interpreter

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

    def visualize(self, chunk):
        self.orchestra.visualize_chunk(chunk, self.id, self.bearing)

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

        self.logger.debug("playing %s at position %fs with duration %fs" % (
                filename, start_time_in_file, segment["duration"]))

        segment["start_time_in_file"] = start_time_in_file
        segment["end_time_in_file"] = end_time_in_file
        self.orchestra.play_segment(segment, self.id, self.bearing)
        return True


class Orchestra:
    SAMPLE_RATE = 44100
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
        self.synth = SynthController()
        self._prepare_players()
        self.stopwatch = Stopwatch()
        self.chunks = self._filter_downloaded_audio_chunks(tr_log.chunks)
        self.score = Interpreter().interpret(self.chunks, tr_log.files)
        self._chunks_by_id = {}
        self.segments_by_id = {}
        self._playing = False
        self._quitting = False
        self._informed_visualizer_about_torrent = False
        self.set_time_cursor(start_time)
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self._run_scheduler_thread()

        if visualizer_enabled:
            self.visualizer = OscSender(VISUALIZER_PORT, osc_log)
            self._setup_osc()
        else:
            self.visualizer = None

    def _filter_downloaded_audio_chunks(self, chunks):
        return filter(lambda chunk: (self._chunk_is_audio(chunk) and
                                     self._chunk_was_downloaded(chunk)),
                      chunks)


    def _chunk_is_audio(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return file_info["is_audio"]

    def _chunk_was_downloaded(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return "decoded_name" in file_info

    def _run_scheduler_thread(self):
        self._scheduler_thread = threading.Thread(target=self._process_scheduled_events)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _process_scheduled_events(self):
        while not self._quitting:
            self.scheduler.run()
            time.sleep(0.01)

    def _setup_osc(self):
        self.server = liblo.Server(PORT)
        self.server.add_method("/visualizing", "if", self._handle_visualizing_message)
        server_thread = threading.Thread(target=self._serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def _serve_osc(self):
        while True:
            self.server.recv(0.01)
            time.sleep(0.01)

    def _handle_visualizing_message(self, path, args, types, src, data):
        (chunk_id, pan) = args
        chunk = self._chunks_by_id[chunk_id]
        self.logger.debug("visualizing chunk %s with pan %s" % (chunk, pan))
        self.synth.pan(chunk["segment_id"], pan)

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
        self._player_class = WavPlayer
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
        no_more_events = False
        while self._playing and not no_more_events:
            event = self._get_next_chunk_or_segment()
            if event:
                self._handle_event(event)
            else:
                no_more_events = True
        self.logger.debug("leaving _play_until_end")

    def _get_next_chunk_or_segment(self):
        self.logger.debug("segment index is %d" % self.current_segment_index)
        chunk = self._get_next_chunk()
        segment = self._get_next_segment()
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
        num_segments = len(self.score)
        while not reached_target:
            chunk = self.chunks[self.current_segment_index]
            if chunk["t"] >= target_log_time:
                reached_target = True
            if not reached_target:
                self.current_segment_index += 1
                if self.current_segment_index == num_segments:
                    reached_target = True
        player = self.get_player_for_chunk(chunk)
        player.play(chunk, pan=0.5)

    def _scrub_backward_to(self, target_log_time):
        reached_target = False
        num_segments = len(self.score)
        while not reached_target:
            chunk = self.chunks[self.current_segment_index]
            if chunk["t"] <= target_log_time:
                reached_target = True
            if not reached_target:
                self.current_segment_index += 1
                if self.current_segment_index < 0 or self.current_segment_index == num_segments:
                    reached_target = True
        player = self.get_player_for_chunk(chunk)
        player.play(chunk, pan=0.5)
        
    def stop(self):
        self.synth.stop_all()
        self._playing = False
        self.log_time_played_from = self.get_current_log_time()
        self.stopwatch.stop()

    def handle_segment(self, segment):
        self.logger.debug("handling segment %s" % segment)
        now = self.get_current_log_time()
        time_margin = segment["onset"] - now
        self.logger.debug("time_margin=%f-%f=%f" % (segment["onset"], now, time_margin))
        player = self.get_player_for_segment(segment)
        self.logger.debug("get_player_for_segment returned %s" % player)
        if not self.realtime and time_margin > 0:
            sleep_time = time_margin
            self.logger.debug("sleeping %f" % sleep_time)
            time.sleep(sleep_time)
        if player:
            self.logger.debug("player.enabled=%s" % player.enabled)
        if player and player.enabled:
            player.play(segment, pan=0.5)

    def handle_chunk(self, chunk):
        self.logger.debug("handling chunk %s" % chunk)
        now = self.get_current_log_time()
        time_margin = chunk["t"] - now
        self.logger.debug("time_margin=%f-%f=%f" % (chunk["t"], now, time_margin))
        player = self.get_player_for_chunk(chunk)
        self.logger.debug("get_player_for_chunk returned %s" % player)
        if not self.realtime and time_margin > 0:
            sleep_time = time_margin
            self.logger.debug("sleeping %f" % sleep_time)
            time.sleep(sleep_time)
        if player:
            self.logger.debug("player.enabled=%s" % player.enabled)
        if player and player.enabled:
            player.visualize(chunk)

    def highlight_segment(self, segment):
        if self.gui:
            self.gui.highlight_segment(segment)

    def visualize_chunk(self, chunk, player_id, bearing):
        if self.visualizer:
            if not self._informed_visualizer_about_torrent:
                self._send_torrent_info_to_visualizer()
            file_info = self.tr_log.files[chunk["filenum"]]
            if not "informed_visualizer" in file_info:
                self._send_file_info_to_visualizer(chunk["filenum"])
            self._chunks_by_id[chunk["id"]] = chunk
            self.visualizer.send("/chunk",
                                 chunk["id"],
                                 chunk["begin"],
                                 chunk["end"] - chunk["begin"],
                                 chunk["filenum"],
                                 player_id,
                                 bearing)

    def visualize_segment(self, segment, player_id, bearing):
        if self.visualizer:
            if not self._informed_visualizer_about_torrent:
                self._send_torrent_info_to_visualizer()
            file_info = self.tr_log.files[segment["filenum"]]
            if not "informed_visualizer" in file_info:
                self._send_file_info_to_visualizer(segment["filenum"])
            self.segments_by_id[segment["id"]] = segment
            self.visualizer.send("/segment",
                                 segment["id"],
                                 segment["begin"],
                                 segment["end"] - segment["begin"],
                                 segment["filenum"],
                                 player_id,
                                 bearing,
                                 segment["duration"])

    def stopped_playing(self, segment):
        self.logger.debug("stopped segment %s" % segment)
        if self.gui:
            self.gui.unhighlight_segment(segment)

    def play_segment(self, segment, player_id, bearing):
        self.segments_by_id[segment["id"]] = segment
        file_info = self.tr_log.files[segment["filenum"]]
        self.synth.play_segment(
            segment["filenum"],
            segment["start_time_in_file"] / file_info["duration"],
            segment["end_time_in_file"] / file_info["duration"],
            segment["duration"],
            segment["pan"])
        self.scheduler.enter(
            segment["duration"], 1,
            self.stopped_playing, [segment])
        self.visualize_segment(segment, player_id, bearing)

    def _send_torrent_info_to_visualizer(self):
        self._informed_visualizer_about_torrent = True
        self.visualizer.send("/torrent", len(self.tr_log.files))

    def _send_file_info_to_visualizer(self, filenum):
        file_info = self.tr_log.files[filenum]
        self.visualizer.send("/file", filenum, file_info["offset"], file_info["length"])
        file_info["informed_visualizer"] = True

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

