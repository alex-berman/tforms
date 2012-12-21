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
from ssr.ssr_control import SsrControl
from space import Space
from predecode import Predecoder

class Server(OscReceiver):
    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("--visualize", dest="visualizer_enabled", action="store_true")
        parser.add_argument("--visualizer", dest="visualizer_command_line")
        parser.add_argument("--osc-log", dest="osc_log")

    def __init__(self, options):
        self.options = options
        self.visualizer = None
        self._orchestra = None
        if options.visualizer_enabled or options.visualizer_command_line:
            self._setup_osc()
            if options.visualizer_command_line:
                self._spawn_visualizer(options.visualizer_command_line)
            self._wait_for_visualizer_to_register()

    def _spawn_visualizer(self, command_line):
        command_line_with_port = "%s -port %d" % (command_line, self.port)
        visualizer_process = subprocess.Popen(command_line_with_port, shell=True, stdin=None)

    def _setup_osc(self):
        self._orchestra_queue = []
        OscReceiver.__init__(self)
        self.add_method("/register", "i", self._handle_register)
        self.add_method("/visualizing", "i", self._handle, "_handle_visualizing_message")
        self.add_method("/set_listener_position", "ff", self._handle, "_handle_set_listener_position")
        self.add_method("/set_listener_orientation", "f", self._handle, "_handle_set_listener_orientation")
        self.add_method("/place_segment", "ifff", self._handle, "_handle_place_segment")
        self.add_method("/enable_smooth_movement", "", self._handle, "_handle_enable_smooth_movement")
        self.add_method("/start_segment_movement_from_peer", "if", self._handle, "_handle_start_segment_movement_from_peer")
        self.start()
        self._visualizer_registered = False
        server_thread = threading.Thread(target=self._serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def _serve_osc(self):
        while True:
            self.serve()
            time.sleep(0.01)

    def _wait_for_visualizer_to_register(self):
        print "waiting for visualizer to register"
        while not self._visualizer_registered:
            time.sleep(0.1)
        print "OK"

    def set_orchestra(self, orchestra):
        self._orchestra = orchestra
        orchestra.server = self
        orchestra.visualizer = self.visualizer
        for args in self._orchestra_queue:
            self._dispatch(*args)
        self._orchestra_queue = []

    def _handle_register(self, path, args, types, src, data):
        visualizer_port = args[0]
        self.visualizer = OscSender(visualizer_port, self.options.osc_log)
        self._visualizer_registered = True

    def _handle(self, *args):
        if self._orchestra:
            self._dispatch(*args)
        else:
            self._orchestra_queue.append(args)

    def _dispatch(self, path, args, types, src, method_name):
        user_data = None
        getattr(self._orchestra, method_name)(path, args, types, src, user_data)

    def shutdown(self):
        if self.visualizer:
            self.visualizer.send("/shutdown")


class Player:
    def __init__(self, orchestra, _id):
        self.orchestra = orchestra
        self.id = _id
        self.enabled = True
        self._previous_chunk_time = None
        self.spatial_position = orchestra.space.new_peer()
        self.trajectory = orchestra.space.parabolic_trajectory_to_listener(
            self.spatial_position.bearing)

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
    JACK = "jack"
    SSR = "ssr"

    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("--rt", action="store_true", dest="realtime")
        parser.add_argument("-t", "--torrent", dest="torrentname", default="")
        parser.add_argument("-z", "--timefactor", dest="timefactor", type=float, default=1)
        parser.add_argument("--start", dest="start_time", type=float, default=0)
        parser.add_argument("-q", "--quiet", action="store_true", dest="quiet")
        parser.add_argument("--pretend-sequential", action="store_true", dest="pretend_sequential")
        parser.add_argument("--gui", action="store_true", dest="gui_enabled")
        parser.add_argument("--predecode", action="store_true", dest="predecode", default=True)
        parser.add_argument("--file-location", dest="file_location", default="../../Downloads")
        parser.add_argument("--fast-forward", action="store_true", dest="ff")
        parser.add_argument("--fast-forward-to-start", action="store_true", dest="ff_to_start")
        parser.add_argument("--quit-at-end", action="store_true", dest="quit_at_end")
        parser.add_argument("--loop", dest="loop", action="store_true")
        parser.add_argument("--max-passivity", dest="max_passivity", type=float)
        parser.add_argument("--max-pause-within-segment", dest="max_pause_within_segment", type=float)
        parser.add_argument("--looped-duration", dest="looped_duration", type=float)
        parser.add_argument("-o", "--output", dest="output", type=str, default=Orchestra.JACK)
        parser.add_argument("--include-non-playable", action="store_true")
        parser.add_argument("-f", "--file", dest="selected_files", type=int, nargs="+")

    _extension_re = re.compile('\.(\w+)$')

    def __init__(self, sessiondir, tr_log, options):
        self.sessiondir = sessiondir
        self.tr_log = tr_log
        self.realtime = options.realtime
        self.timefactor = options.timefactor
        self.quiet = options.quiet
        self.predecode = options.predecode
        self.file_location = options.file_location
        self._loop = options.loop
        self._max_passivity = options.max_passivity
        self.looped_duration = options.looped_duration
        self.output = options.output
        self.include_non_playable = options.include_non_playable
        self._visualizer_enabled = (options.visualizer_enabled or options.visualizer_command_line)

        if options.predecode:
            predecoder = Predecoder(tr_log, options.file_location, self.SAMPLE_RATE)
            predecoder.decode()

        if options.selected_files:
            tr_log.select_files(options.selected_files)

        self.playback_enabled = True
        self.fast_forwarding = False
        self._log_time_for_last_handled_event = 0
        self.gui = None
        self._check_which_files_are_audio()
        self.synth = SynthController()
        self._create_players()
        self._prepare_playable_files()
        self.stopwatch = Stopwatch()
        self.playable_chunks = self._filter_playable_chunks(tr_log.chunks)

        if self.include_non_playable:
            self.chunks = tr_log.chunks
            self._num_selected_files = len(self.tr_log.files)
        else:
            self.chunks = self.playable_chunks
            self._num_selected_files = self._num_playable_files
        logger.debug("total num chunks: %s" % len(tr_log.chunks))
        logger.debug("num playable chunks: %s" % len(self.playable_chunks))
        logger.debug("num selected chunks: %s" % len(self.chunks))

        self._interpret_chunks_to_score(options.max_pause_within_segment)
        self._chunks_by_id = {}
        self.segments_by_id = {}
        self._playing = False
        self._quitting = False
        self._informed_visualizer_about_torrent = False
        self.space = Space()

        if options.ff_to_start:
            self._ff_to_time = options.start_time
            self.set_time_cursor(0)
        else:
            self._ff_to_time = None
            self.set_time_cursor(options.start_time)

        self.scheduler = sched.scheduler(time.time, time.sleep)
        self._run_scheduler_thread()

        if self.output == self.SSR:
            self.ssr = SsrControl()
            self._warned_about_max_sources = False
        else:
            self.ssr = None

    def _interpret_chunks_to_score(self, max_pause_within_segment):
        self.score = Interpreter(max_pause_within_segment).interpret(self.playable_chunks, self.tr_log.files)
        if self._max_passivity:
            self._reduce_max_passivity_in_score()
        for segment in self.score:
            segment["duration"] /= self.timefactor

    def _reduce_max_passivity_in_score(self):
        previous_onset = 0
        reduced_time = 0
        for i in range(len(self.score)):
            if (self.score[i]["onset"] - reduced_time - previous_onset) > self._max_passivity:
                reduced_time += self.score[i]["onset"] - reduced_time - previous_onset - self._max_passivity
            self.score[i]["onset"] -= reduced_time
            previous_onset = self.score[i]["onset"]

    def _filter_playable_chunks(self, chunks):
        return filter(lambda chunk: (self._chunk_is_playable(chunk)),
                      chunks)


    def _chunk_is_playable(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return file_info["playable_file_index"] != -1

    def _run_scheduler_thread(self):
        self._scheduler_thread = threading.Thread(target=self._process_scheduled_events)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _process_scheduled_events(self):
        while not self._quitting:
            self.scheduler.run()
            time.sleep(0.01)

    def _handle_visualizing_message(self, path, args, types, src, data):
        segment_id = args[0]
        segment = self.segments_by_id[segment_id]
        logger.debug("visualizing segment %s" % segment)
        if self.output == self.SSR:
            if segment["sound_source_id"]:
                channel = segment["sound_source_id"] - 1
                self._ask_synth_to_play_segment(segment, channel=channel, pan=None)
        else:
            self._ask_synth_to_play_segment(segment, channel=0, pan=0.5)

    def _ask_synth_to_play_segment(self, segment, channel, pan):
        logger.debug("asking synth to play %s" % segment)
        file_info = self.tr_log.files[segment["filenum"]]

        self.synth.play_segment(
            segment["id"],
            segment["filenum"],
            segment["start_time_in_file"] / file_info["duration"],
            segment["end_time_in_file"] / file_info["duration"],
            segment["duration"],
            self.looped_duration,            
            channel,
            pan)
        self.scheduler.enter(
            segment["playback_duration"], 1,
            self.stopped_playing, [segment])

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
        if self.predecode:
            self._get_wav_files_info()
            self._load_sounds()
        else:
            raise Exception("playing wav without precoding is not supported")

    def _load_sounds(self):
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if file_info["playable_file_index"] != -1:
                logger.debug("load_sound(%s)" % file_info["decoded_name"])
                result = self.synth.load_sound(filenum, file_info["decoded_name"])
                logger.debug("result: %s" % result)

    def _get_wav_files_info(self):
        playable_file_index = 0
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            file_info["playable_file_index"] = -1

            if "decoded_name" in file_info:
                file_info["duration"] = self._get_file_duration(file_info)
                if file_info["duration"] > 0:
                    file_info["num_channels"] = self._get_num_channels(file_info)
                    file_info["playable_file_index"] = playable_file_index
                    logger.debug("duration for %r: %r\n" %
                                      (file_info["name"], file_info["duration"]))
                    playable_file_index += 1

            if self.include_non_playable:
                file_info["index"] = filenum
            else:
                file_info["index"] = file_info["playable_file_index"]
        self._num_playable_files = playable_file_index

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
        if len(self.score) == 0:
            return None
        elif self.current_segment_index < len(self.score):
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
        if not player:
            logger.debug("get_player_for_segment returned None - skipping playback")

        if self.fast_forwarding:
            self._stop_ff_if_necessary()
        else:
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

        if self.fast_forwarding:
            self._stop_ff_if_necessary()
        else:
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

    def _stop_ff_if_necessary(self):
        if self._ff_to_time is not None and \
                self._log_time_for_last_handled_event >= self._ff_to_time:
            self._ff_to_time = None
            self.fast_forwarding = False
            self.set_time_cursor(self.log_time_played_from)

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
                                 file_info["index"],
                                 player.id,
                                 chunk["t"])

    def visualize_segment(self, segment, player):
        if self.visualizer:
            if self.ssr:
                segment["sound_source_id"] = self.ssr.allocate_source()
                if not segment["sound_source_id"] and not self._warned_about_max_sources:
                    print "WARNING: max sources exceeded, skipping segment playback (this warning will not be repeated)"
                    self._warned_about_max_sources = True

            if not self._informed_visualizer_about_torrent:
                self._send_torrent_info_to_visualizer()
            file_info = self.tr_log.files[segment["filenum"]]
            self.segments_by_id[segment["id"]] = segment
            self.visualizer.send("/segment",
                                 segment["id"],
                                 segment["begin"],
                                 segment["end"] - segment["begin"],
                                 file_info["index"],
                                 player.id,
                                 segment["t"],
                                 segment["playback_duration"])
        else:
            self._ask_synth_to_play_segment(segment, channel=0, pan=0.5)

    def stopped_playing(self, segment):
        logger.debug("stopped segment %s" % segment)
        if self.gui:
            self.gui.unhighlight_segment(segment)
        if self.visualizer:
            if self.ssr and segment["sound_source_id"]:
                self.ssr.free_source(segment["sound_source_id"])

    def play_segment(self, segment, player):
        self.segments_by_id[segment["id"]] = segment

        if self.looped_duration:
            segment["playback_duration"] = self.looped_duration
        else:
            segment["playback_duration"] = segment["duration"]

        self.visualize_segment(segment, player)

    def _send_torrent_info_to_visualizer(self):
        self._informed_visualizer_about_torrent = True
        self.visualizer.send("/torrent",
                             self._num_selected_files,
                             self.tr_log.lastchunktime(),
                             self.tr_log.total_file_size())
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if self.include_non_playable or file_info["playable_file_index"] != -1:
                self.visualizer.send("/file",
                                     file_info["index"],
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
            peer_player = self._create_player(peeraddr)
            self.players.append(peer_player)
            self._player_for_peer[peeraddr] = peer_player
        return peer_player

    def _create_player(self, addr):
        count = len(self.players)
        logger.debug("creating player number %d" % count)
        player = self._player_class(self, count)
        if self.visualizer:
            self.visualizer.send("/peer", player.id, addr, player.spatial_position.bearing)
        return player

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

    def _handle_set_listener_position(self, path, args, types, src, data):
        if self.ssr:
            x, y = args
            self.ssr.set_listener_position(x, y)

    def _handle_set_listener_orientation(self, path, args, types, src, data):
        if self.ssr:
            orientation = args[0]
            self.ssr.set_listener_orientation(orientation)

    def _handle_place_segment(self, path, args, types, src, data):
        segment_id, x, y, duration = args
        if self.ssr:
            segment = self.segments_by_id[segment_id]
            sound_source_id = segment["sound_source_id"]
            if sound_source_id is not None:
                self.ssr.place_source(sound_source_id, x, y, duration)
        else:
            pan = self._spatial_position_to_stereo_pan(x, y)
            self.synth.pan(segment_id, pan)

    def _handle_enable_smooth_movement(self, path, args, types, src, data):
        if self.ssr:
            self.ssr.enable_smooth_movement()

    def _handle_start_segment_movement_from_peer(self, path, args, types, src, data):
        segment_id, duration = args
        if self.ssr:
            segment = self.segments_by_id[segment_id]
            sound_source_id = segment["sound_source_id"]
            if sound_source_id is not None:
                player = self.get_player_for_segment(segment)
                self.ssr.start_source_movement(
                    sound_source_id, player.trajectory, duration)

    def _spatial_position_to_stereo_pan(self, x, y):
        # compare rectangular_visualizer.Visualizer.pan_segment
        # NOTE: assumes default listener position and orientation!
        return float(x) / 5 + 0.5

    def reset(self):
        self._free_sounds()
        if self.visualizer:
            self.visualizer.send("/reset")

    def _free_sounds(self):
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if file_info["playable_file_index"] != -1:
                self.synth.free_sound(filenum)

def warn(logger, message):
    logger.debug(message)
    print >> sys.stderr, "WARNING: %s" % message

