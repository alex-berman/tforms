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
from logger_factory import logger
from osc_sender import OscSender
from interpret import Interpreter
from stopwatch import Stopwatch
from ssr.ssr_control import SsrControl
from space import Space
from predecode import Predecoder
import socket
import datetime
import Queue

class VisualizerConnector:
    remote_matcher = re.compile('^remote:(.*)$')
    shell_matcher = re.compile('^(shell:)?(.*)$')

    def __init__(self, spec, server):
        self.spec = spec
        self.server = server
        remote_match = self.remote_matcher.match(spec)
        shell_match = self.shell_matcher.match(spec)
        if remote_match:
            self.host = remote_match.group(1)
        elif shell_match:
            self.host = self.server.host
            command_line = shell_match.group(2)
            self._spawn_visualizer(command_line)
        else:
            raise Exception("failed to parse visualizer spec %r" % spec)
        self._reset()

    def _reset(self):
        self.informed_about_torrent = False
        self.informed_about_peer = {}
        self.connected = False

    def _spawn_visualizer(self, command_line):
        command_line_with_port = "%s -port %d" % (command_line, self.server.port)
        subprocess.Popen(command_line_with_port, shell=True, stdin=None)

    def connect_to(self, port):
        self._sender = OscSender(
            host=self.host,
            port=port)
        self.connected = True

    def send(self, *args):
        if self.connected:
            try:
                self._sender.send(*args)
                return True
            except IOError:
                warn(logger, "failed to send to visualizer %r - ignoring it from now on" % self.spec)
                self._reset()

class Server(OscReceiver):
    @staticmethod
    def add_parser_arguments(parser):
        parser.add_argument("--visualizer", type=str, action="append")
        parser.add_argument("-port", type=int)
        parser.add_argument("--no-synth", action="store_true")
        parser.add_argument("--locate-peers", action="store_true")
        parser.add_argument("--sc-mode", type=str, default="default_stereo")
        parser.add_argument("--predecode", action="store_true", dest="predecode", default=True)
        parser.add_argument("--force-predecode", action="store_true")

    def __init__(self, options):
        self.options = options
        self.visualizers = []
        self._orchestra = None
        if options.visualizer:
            self._setup_osc()
            self._save_port_to_disk()
            for visualizer_spec in options.visualizer:
                visualizer = VisualizerConnector(visualizer_spec, self)
                self.visualizers.append(visualizer)
            self._wait_for_visualizers_to_register()

        if not options.no_synth:
            from synth_controller import SynthController
            SynthController.kill_potential_engine_from_previous_process()

        if options.locate_peers:
            import geo.ip_locator
            self.ip_locator = geo.ip_locator.IpLocator()

    def _setup_osc(self):
        self.host = socket.gethostbyname(socket.gethostname())
        self._orchestra_queue = []
        OscReceiver.__init__(self, port=self.options.port, name="Server")
        self.add_method("/register", "i", self._handle_register)
        self.add_method("/visualizing", "i", self._handle, "_handle_visualizing_message")
        self.add_method("/set_listener_position", "ff", self._handle, "_handle_set_listener_position")
        self.add_method("/set_listener_orientation", "f", self._handle, "_handle_set_listener_orientation")
        self.add_method("/place_segment", "ifff", self._handle, "_handle_place_segment")
        self.add_method("/enable_smooth_movement", "", self._handle, "_handle_enable_smooth_movement")
        self.add_method("/start_segment_movement_from_peer", "if", self._handle, "_handle_start_segment_movement_from_peer")
        self.add_method("/finished", "", self._handle, "_handle_finished")
        self.start()
        self._num_registered_visualizers = 0
        server_thread = threading.Thread(name="%s.server_thread" % self.__class__.__name__,
                                         target=self._serve_osc)
        server_thread.daemon = True
        server_thread.start()

    def _save_port_to_disk(self):
        f = open("server_port.txt", "w")
        print >>f, self.port
        f.close()

    def _serve_osc(self):
        while True:
            self.serve()
            time.sleep(0.01)

    def _wait_for_visualizers_to_register(self):
        print "waiting for %s visualizer(s) to register at %s:%s" % (
            len(self.visualizers), self.host, self.port)
        while self._num_registered_visualizers < len(self.visualizers):
            time.sleep(0.1)

    def set_orchestra(self, orchestra):
        self._orchestra = orchestra
        orchestra.server = self
        orchestra.visualizers = self.visualizers
        if self.options.visualizer:
            for args in self._orchestra_queue:
                self._dispatch(*args)
            self._orchestra_queue = []
        orchestra.init_playback()

    def _handle_register(self, path, args, types, src, data):
        visualizer_port = args[0]
        for connector in self.visualizers:
            if not connector.connected:
                connector.connect_to(visualizer_port)
                print "visualizer registered: %r" % connector.spec
                self._num_registered_visualizers = len(filter(lambda visualizer: visualizer.connected,
                                                              self.visualizers))
                return
        warn(logger, "cannot register visualizer: all connectors already connected!")

    def _handle(self, *args):
        if self._orchestra:
            self._dispatch(*args)
        else:
            self._orchestra_queue.append(args)

    def _dispatch(self, path, args, types, src, method_name):
        user_data = None
        getattr(self._orchestra, method_name)(path, args, types, src, user_data)

    def shutdown(self):
        self._tell_visualizers("/shutdown")

    def _tell_visualizers(self, *args):
        for visualizer in self.visualizers:
            visualizer.send(*args)


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
        if self.orchestra.options.pretend_audio_filename:
            segment["audio_filenum"] = 0
            file_info = self.orchestra.tr_log.files[segment["audio_filenum"]]
            begin = segment["begin"]
            end = segment["end"]
        else:
            segment["audio_filenum"] = segment["filenum"]
            file_info = self.orchestra.tr_log.files[segment["audio_filenum"]]
            begin = segment["begin"] - file_info["offset"]
            end = segment["end"] - file_info["offset"]

        filename = file_info["decoded_name"]
        start_time_in_file = self._bytecount_to_secs(begin, file_info)
        end_time_in_file = self._bytecount_to_secs(end, file_info)

        logger.debug("playing %s at position %fs with duration %fs" % (
                filename, start_time_in_file, segment["duration"]))

        audio_file_duration = file_info["duration"]
        segment["relative_start_time_in_file"] = start_time_in_file / audio_file_duration
        segment["relative_end_time_in_file"] = end_time_in_file / audio_file_duration
        self.orchestra.play_segment(segment, self)
        return True


class Orchestra:
    SAMPLE_RATE = 44100
    BYTES_PER_SAMPLE = 2 # mpg123, used by predecode, outputs 16-bit PCM mono
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
        parser.add_argument("--fast-forward", action="store_true", dest="ff")
        parser.add_argument("--fast-forward-to-start", action="store_true", dest="ff_to_start")
        parser.add_argument("--quit-at-end", action="store_true", dest="quit_at_end")
        parser.add_argument("--loop", dest="loop", action="store_true")
        parser.add_argument("--max-pause-within-segment", type=float)
        parser.add_argument("--max-segment-duration", type=float)
        parser.add_argument("--looped-duration", dest="looped_duration", type=float)
        parser.add_argument("-o", "--output", dest="output", type=str, default=Orchestra.JACK)
        parser.add_argument("--include-non-playable", action="store_true")
        parser.add_argument("-f", "--file", dest="selected_files", type=int, nargs="+")
        parser.add_argument("--title", type=str, default="")
        parser.add_argument("--pretend-audio", dest="pretend_audio_filename")
        parser.add_argument("--capture-audio", action="store_true")

    _extension_re = re.compile('\.(\w+)$')

    def __init__(self, server, sessiondir, tr_log, options):
        self.server = server
        self.options = options
        self.sessiondir = sessiondir
        self.tr_log = tr_log
        self.realtime = options.realtime
        self.timefactor = options.timefactor
        self.quiet = options.quiet
        self._loop = options.loop
        self.looped_duration = options.looped_duration
        self.output = options.output
        self.include_non_playable = options.include_non_playable

        if server.options.locate_peers:
            self._peer_location = {}
            for peeraddr in tr_log.peers:
                self._peer_location[peeraddr] = server.ip_locator.locate(peeraddr)
            self._peers_center_location_x = self._get_peers_center_location_x()

        if options.pretend_audio_filename:
            self._pretended_file = self._fileinfo_for_pretended_audio_file()
            self._pretended_file["duration"] = self._get_file_duration(self._pretended_file)
            self._pretended_files = [self._pretended_file]
            self._files_to_play = self._pretended_files
        else:
            self._files_to_play = self.tr_log.files

        self.predecode = server.options.predecode
        if self.predecode:
            predecoder = Predecoder(
                tr_log.files, sample_rate=self.SAMPLE_RATE, location=tr_log.file_location)
            predecoder.decode(server.options.force_predecode)

            if options.pretend_audio_filename:
                predecoder = Predecoder(
                    self._pretended_files, sample_rate=self.SAMPLE_RATE)
                predecoder.decode(server.options.force_predecode)

        if options.selected_files:
            tr_log.select_files(options.selected_files)

        self.playback_enabled = True
        self.fast_forwarding = False
        self.gui = None
        self._check_which_files_are_audio()

        self._player_class = WavPlayer
        self.players = []
        self._player_for_peer = dict()

        self._prepare_playable_files()
        self.stopwatch = Stopwatch()
        self.playable_chunks = self._filter_playable_chunks(tr_log, tr_log.chunks)

        if self.include_non_playable:
            self.chunks = tr_log.chunks
            self._num_selected_files = len(self.tr_log.files)
        else:
            self.chunks = self.playable_chunks
            self._num_selected_files = self._num_playable_files
        logger.debug("total num chunks: %s" % len(tr_log.chunks))
        logger.debug("num playable chunks: %s" % len(self.playable_chunks))
        logger.debug("num selected chunks: %s" % len(self.chunks))

        self.score = self._interpret_chunks_to_score(tr_log, self.playable_chunks, options)
        self.estimated_duration = self._estimated_playback_duration(self.score, options)
        print "playback duration: %s" % datetime.timedelta(seconds=self.estimated_duration)
        self._chunks_by_id = {}
        self.segments_by_id = {}
        self._playing = False
        self._quitting = False
        self._was_stopped = False
        self.space = Space()

        self._scheduler_queue = Queue.Queue()
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self._run_scheduler_thread()

        if self.output == self.SSR:
            self.ssr = SsrControl()
            self._warned_about_max_sources = False

    def init_playback(self):
        if self.server.options.no_synth:
            self.synth = None
        else:
            from synth_controller import SynthController
            self.synth = SynthController()
            self.synth.launch_engine(self.server.options.sc_mode)
            self.synth.connect(self.synth.lang_port)
            self.synth.subscribe_to_info()
            if self.options.capture_audio:
                self._load_sounds()
                self._start_capture_audio()
            self._tell_visualizers("/synth_address", self.synth.lang_port)

            if self.output == self.SSR:
                self.ssr.run()

        if not self.options.capture_audio:
            self._load_sounds()

        self._log_time_for_last_handled_event = 0
        if self.options.ff_to_start:
            self._ff_to_time = self.options.start_time
            self.set_time_cursor(0)
        else:
            self._ff_to_time = None
            self.set_time_cursor(self.options.start_time)

    def _start_capture_audio(self):
        self._audio_capture_filename = "capture.wav"
        if os.path.exists(self._audio_capture_filename):
            os.remove(self._audio_capture_filename)
        self._audio_capture_process = subprocess.Popen(
            ["./jack_capture/jack_capture", "-f", self._audio_capture_filename, "-d", "-1",
             "SuperCollider:out_1", "SuperCollider:out_2"],
            shell=False)
        self._wait_until_audio_capture_started()
    
    def _wait_until_audio_capture_started(self):
        while not os.path.exists(self._audio_capture_filename):
            time.sleep(0.1)

    @classmethod
    def _estimated_playback_duration(cls, score, options):
        last_segment = score[-1]
        return last_segment["onset"] / options.timefactor + last_segment["duration"]

    @classmethod
    def _interpret_chunks_to_score(cls, tr_log, chunks, options):
        score = Interpreter(options.max_pause_within_segment,
                            options.max_segment_duration).interpret(
            chunks, tr_log.files)
        for segment in score:
            segment["duration"] /= options.timefactor
        return score

    @classmethod
    def _filter_playable_chunks(cls, tr_log, chunks):
        return filter(lambda chunk: (cls._chunk_is_playable(tr_log, chunk)),
                      chunks)

    @classmethod
    def _chunk_is_playable(cls, tr_log, chunk):
        file_info = tr_log.files[chunk["filenum"]]
        return file_info["playable_file_index"] != -1

    def _run_scheduler_thread(self):
        self._scheduler_thread = threading.Thread(target=self._process_scheduled_events)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _process_scheduled_events(self):
        while not self._quitting:
            while True:
                try:
                    delay, priority, action, arguments = self._scheduler_queue.get(True, 0.01)
                except Queue.Empty:
                    break
                self.scheduler.enter(delay, priority, action, arguments)
            self.scheduler.run()

    def _handle_visualizing_message(self, path, args, types, src, data):
        segment_id = args[0]
        segment = self.segments_by_id[segment_id]
        logger.debug("visualizing segment %s" % segment)
        player = self.get_player_for_segment(segment)
        self._ask_synth_to_play_segment(segment, channel=0, pan=player.spatial_position.pan)

    def _ask_synth_to_play_segment(self, segment, channel, pan):
        if self.synth:
            logger.debug("asking synth to play %s" % segment)
            file_info = self.tr_log.files[segment["filenum"]]

            if self.output == self.SSR:
                segment["sound_source_id"] = self.ssr.allocate_source()
                if segment["sound_source_id"] and not self._warned_about_max_sources:
                    channel = segment["sound_source_id"] - 1
                    pan = None
                else:
                    print "WARNING: max sources exceeded, skipping segment playback (this warning will not be repeated)"
                    self._warned_about_max_sources = True
                    return

            self.synth.play_segment(
                segment["id"],
                segment["audio_filenum"],
                segment["relative_start_time_in_file"],
                segment["relative_end_time_in_file"],
                segment["duration"],
                self.looped_duration,            
                channel,
                pan)
        self._scheduler_queue.put(
            (segment["playback_duration"], 1, self.stopped_playing, [segment]))

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

    def _prepare_playable_files(self):
        if self.predecode:
            self._num_playable_files = self._get_wav_files_info(
                self.tr_log, self.include_non_playable)
        else:
            raise Exception("playing wav without precoding is not supported")

    def _load_sounds(self):
        if self.synth:
            print "loading sounds"
            for filenum in range(len(self._files_to_play)):
                file_info = self._files_to_play[filenum]
                if file_info["playable_file_index"] != -1:
                    logger.info("load_sound(%s)" % file_info["decoded_name"])
                    result = self._load_sound_stubbornly(filenum, file_info["decoded_name"])
                    logger.info("load_sound result: %s" % result)
            print "OK"

    def _load_sound_stubbornly(self, filenum, filename):
        while True:
            result = self.synth.load_sound(filenum, filename)
            if result > 0:
                return result
            else:
                warn(logger, "synth returned %s - retrying soon" % result)
                time.sleep(1.0)

    @classmethod
    def _get_wav_files_info(cls, tr_log, include_non_playable=False):
        playable_file_index = 0
        for filenum in range(len(tr_log.files)):
            file_info = tr_log.files[filenum]
            file_info["playable_file_index"] = -1

            if "decoded_name" in file_info:
                file_info["duration"] = cls._get_file_duration(file_info)
                if file_info["duration"] > 0:
                    file_info["playable_file_index"] = playable_file_index
                    logger.debug("duration for %r: %r\n" %
                                      (file_info["name"], file_info["duration"]))
                    playable_file_index += 1

            if include_non_playable:
                file_info["index"] = filenum
            else:
                file_info["index"] = file_info["playable_file_index"]
        return playable_file_index

    @classmethod
    def _get_file_duration(cls, file_info):
        if "decoded_name" in file_info:
            statinfo = os.stat(file_info["decoded_name"])
            wav_header_size = 44
            return float((statinfo.st_size - wav_header_size) / cls.BYTES_PER_SAMPLE) / cls.SAMPLE_RATE

    def get_current_log_time(self):
        if self.fast_forwarding:
            return self._log_time_for_last_handled_event
        else:
            return self.log_time_played_from + self.stopwatch.get_elapsed_time() * self.timefactor

    def play_non_realtime(self, quit_on_end=False):
        logger.info("entering play_non_realtime")
        self._was_stopped = False
        self._num_finished_visualizers = 0
        if self._loop:
            while True:
                self._play_until_end()
                if not self._was_stopped:
                    self._wait_for_visualizers_to_finish()
                self.set_time_cursor(0)
        else:
            self._play_until_end()
            if not self._was_stopped:
                self._wait_for_visualizers_to_finish()
            if quit_on_end:
                self._quit()
        logger.info("leaving play_non_realtime")

    def _quit(self):
        if self.options.capture_audio:
            self._audio_capture_process.kill()
        self._quitting = True

    def _play_until_end(self):
        logger.info("entering _play_until_end")
        self._playing = True
        self.stopwatch.start()
        no_more_events = False
        while self._playing and not no_more_events:
            event = self._get_next_chunk_or_segment()
            if event:
                self._handle_event(event)
            else:
                no_more_events = True
        logger.info("leaving _play_until_end")

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
        # stop_all disabled as it also deletes ~reverb
        # if self.synth:
        #     self.synth.stop_all()
        self._was_stopped = True
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
        if len(self.visualizers) > 0:
            self._inform_visualizers_about_peer(player)
            file_info = self.tr_log.files[chunk["filenum"]]
            self._chunks_by_id[chunk["id"]] = chunk
            self._tell_visualizers(
                "/chunk",
                chunk["id"],
                chunk["begin"],
                chunk["end"] - chunk["begin"],
                file_info["index"],
                player.id,
                chunk["t"])

    def visualize_segment(self, segment, player):
        if len(self.visualizers) > 0:
            self._inform_visualizers_about_peer(player)
            file_info = self.tr_log.files[segment["filenum"]]
            self.segments_by_id[segment["id"]] = segment
            self._tell_visualizers(
                "/segment",
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
        if self.output == self.SSR and segment["sound_source_id"]:
            self.ssr.free_source(segment["sound_source_id"])

    def play_segment(self, segment, player):
        self.segments_by_id[segment["id"]] = segment

        if self.looped_duration:
            segment["playback_duration"] = self.looped_duration
        else:
            segment["playback_duration"] = segment["duration"]

        self.visualize_segment(segment, player)

    def _send_torrent_info_to_uninformed_visualizers(self):
        for visualizer in self.visualizers:
            if not visualizer.informed_about_torrent:
                self._send_torrent_info_to_visualizer(visualizer)

    def _inform_visualizers_about_peer(self, player):
        for visualizer in self.visualizers:
            if player.id not in visualizer.informed_about_peer:
                if visualizer.send(
                    "/peer", player.id, player.addr, player.spatial_position.bearing,
                    player.spatial_position.pan, player.location_str):
                    visualizer.informed_about_peer[player.id] = True

    def _send_torrent_info_to_visualizer(self, visualizer):
        if not visualizer.send(
            "/torrent",
            self._num_selected_files,
            self.tr_log.lastchunktime(),
            self.tr_log.total_file_size(),
            len(self.chunks),
            len(self.score),
            self.options.title):
            return
        for filenum in range(len(self.tr_log.files)):
            file_info = self.tr_log.files[filenum]
            if self.include_non_playable or file_info["playable_file_index"] != -1:
                if not visualizer.send(
                    "/file",
                    file_info["index"],
                    file_info["offset"],
                    file_info["length"]):
                    return
        visualizer.informed_about_torrent = True

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
        player.addr = addr
        if self.server.options.locate_peers and self._peer_location[addr] is not None:
            x, y, place_name = self._peer_location[addr]
            if place_name:
                place_name = place_name.encode("unicode_escape")
            else:
                place_name = ""
            player.location_str = "%s,%s,%s" % (x, y, place_name)

            if x < self._peers_center_location_x:
                player.spatial_position.pan = -1.0
            else:
                player.spatial_position.pan = 1.0
        else:
            player.location_str = ""
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
        if self.output == self.SSR:
            x, y = args
            self.ssr.set_listener_position(x, y)

    def _handle_set_listener_orientation(self, path, args, types, src, data):
        if self.output == self.SSR:
            orientation = args[0]
            self.ssr.set_listener_orientation(orientation)

    def _handle_place_segment(self, path, args, types, src, data):
        segment_id, x, y, duration = args
        if self.output == self.SSR:
            segment = self.segments_by_id[segment_id]
            sound_source_id = segment["sound_source_id"]
            if sound_source_id is not None:
                self.ssr.place_source(sound_source_id, x, y, duration)
        else:
            pan = self._spatial_position_to_stereo_pan(x, y)
            if self.synth:
                self.synth.pan(segment_id, pan)

    def _handle_enable_smooth_movement(self, path, args, types, src, data):
        pass # OBSOLETE after smooth movement made default

    def _handle_start_segment_movement_from_peer(self, path, args, types, src, data):
        segment_id, duration = args
        if self.output == self.SSR:
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
        if self.synth:
            self.synth.stop_engine()
        self._tell_visualizers("/reset")
        for visualizer in self.visualizers:
            visualizer.informed_about_torrent = False
            visualizer.informed_about_peer = {}

    def _tell_visualizers(self, *args):
        self._send_torrent_info_to_uninformed_visualizers()
        self.server._tell_visualizers(*args)

    def _fileinfo_for_pretended_audio_file(self):
        return {"offset": 0,
                "length": os.stat(self.options.pretend_audio_filename).st_size,
                "name": self.options.pretend_audio_filename,
                "playable_file_index": 0}

    def _handle_finished(self, path, args, types, src, data):
        self._num_finished_visualizers += 1

    def _wait_for_visualizers_to_finish(self):
        while self._num_finished_visualizers < len(self.visualizers):
            time.sleep(0.1)

    def _get_peers_center_location_x(self):
        if len(self._peer_location) <= 1:
            return 0
        else:
            sorted_xs = sorted([x for x,y,location_str in self._peer_location.values()])
            center_index = int((len(self._peer_location)-1) / 2)
            return float(sorted_xs[center_index] + sorted_xs[center_index+1]) / 2

def warn(logger, message):
    logger.info(message)
    print >> sys.stderr, "WARNING: %s" % message
