import time
import subprocess
import threading
from tr_log_reader import TrLogReader
import random
from audio_buffer import *
import sys
import os
import re
from space import StereoSpace
import Queue
import liblo

VISUALIZER_PORT = 51234

def clamp(value, mini, maxi):
    if value < mini:
        return mini
    elif value > maxi:
        return maxi
    else:
        return value


class Player:
    def __init__(self, orchestra, _id, pan):
        self.orchestra = orchestra
        self.logger = orchestra.logger
        self.id = _id
        self.pan = pan
        self.enabled = True
        if self.orchestra.audio_engine == 'alsa':
            cmd = "aplay -f S16_LE -c 2 -r %d -t raw -" % Orchestra.SAMPLE_RATE
        elif self.orchestra.audio_engine == 'jack':
            cmd = 'mplayer -rawaudio samplesize=2:channels=2:rate=%d -demuxer rawaudio ' \
                '-ao jack:port=%s -' % (Orchestra.SAMPLE_RATE, self.orchestra.output_device)
        self.output = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
        self._sox_mixer = {1: self._pan_to_sox_mixer_mono(pan),
                           2: self._pan_to_sox_mixer_stereo(pan)}
        self._previous_chunk_time = None
        self._chunk_queue = Queue.Queue()
        processing_thread = threading.Thread(target=self._processing_loop)
        processing_thread.daemon = True
        processing_thread.start()

    def play(self, chunk, desired_time=None):
        self._chunk_queue.put((chunk, desired_time))

    def _processing_loop(self):
        while True:
            chunk, desired_time = self._chunk_queue.get(True)
            self._play(chunk, desired_time)

    def _play(self, chunk, desired_time):
        command = self.interpret_sonically(chunk, desired_time)
        if command:
            self.orchestra.highlight_chunk(chunk)
            subprocess.Popen(
                command, shell=True, stdout=self.output.stdin).wait()

    def interpret_sonically(self, chunk, desired_time):
        command = self.get_command_for_sonic_interpretation(chunk, desired_time)
        self._previous_chunk_time = desired_time
        return command

    def _bytecount_to_secs(self, byte_count, file_info):
        duration_secs = file_info["duration"]
        file_num_bytes = file_info["length"]
        return duration_secs * byte_count / file_num_bytes

    def _pan_to_sox_mixer_stereo(self, pan):
        ll = rl = (1 - pan) / 2
        lr = rr = pan / 2
        return 'mixer %f,%f,%f,%f' % (ll, lr, rl, rr)

    def _pan_to_sox_mixer_mono(self, pan):
        return 'remix 1 1 mixer %f' % ((1 - pan) / 2)




class MP3Player(Player):
    MPG123_EXEC = "mpg123-1.13.2/src/mpg123"
    #MPG123_EXEC = "mpg123"
    BUFFER_SIZE = 100000
    FADE_TIME = 0.1

    def __init__(self, orchestra, _id, pan):
        Player.__init__(self, orchestra, _id, pan)
        decoder_cmdline = "%s %s -s -0 -" % (self.MPG123_EXEC,
                                             self.orchestra.mpg123_options)
        self.decoder = subprocess.Popen(decoder_cmdline,
                                        shell=True,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE
                                        #stderr=subprocess.PIPE
                                        )
        if not self.decoder:
            raise Exception("failed to spawn decoder (command line '%s')" % decoder_cmdline)
        self.terminated = False

    def play(self, chunk):
        filename = "%s/chunks/chunk%06d" % (self.orchestra.sessiondir, chunk["id"])
        f = open(filename, "rb")
        contents = f.read()
        f.close()
        try:
            self.decoder.stdin.write(contents)
        except IOError as err:
            warn(self.logger, "error when writing to decoder: %s" % err)
            self.terminated = True
            return

    def processing_loop(self):
        while not self.terminated:
            try:
                raw_buffer = self.decoder.stdout.read(self.BUFFER_SIZE)
            except IOError as err:
                warn(self.logger, "error when reading from worker: %s" % err)
                self.terminated = True
            if not self.terminated:
                self.process_raw_buffer(raw_buffer)

    def process_raw_buffer(self, raw_buffer):
        fragment = AudioBuffer.from_raw_mono_data(raw_buffer, Orchestra.SAMPLE_RATE)
        #fragment.apply_fade(self.FADE_TIME)
        #fragment.apply_pan_right_to_left()
        try:
            self.output.stdin.write(fragment.to_raw_data())
        except IOError as err:
            warn(self.logger, "error when writing to audio device: %s" % err)
            self.terminated = True


class WavPlayer(Player):
    def get_command_for_sonic_interpretation(self, chunk, desired_time):
        command = None
        if desired_time == None or self._previous_chunk_time:
            file_info = self.orchestra.tr_log.files[chunk["filenum"]]
            filename = file_info["decoded_name"]
            start_secs = self._bytecount_to_secs(chunk["begin"]-file_info["offset"], file_info)
            length_secs = self._bytecount_to_secs(chunk["end"]-chunk["begin"], file_info)

            if desired_time == None:
                stretch_effect = ''
            else:
                desired_duration = desired_time - self._previous_chunk_time
                if desired_duration == 0:
                    warn(self.logger, "simultaneous chunks within a peer?")
                    desired_duration = 0.01
                
                if desired_duration > Orchestra.MAX_GRAIN_DURATION:
                    self.logger.debug("skipping chunk after long pause")
                    self._previous_chunk_time = desired_time
                    return None
                else:
                    time_factor = length_secs / desired_duration
                    self.logger.debug("desired_duration=%f" % desired_duration)
                    if self.orchestra.speed_metaphor == Orchestra.STRETCH:
                        time_factor = clamp(time_factor, 0.1, 100)
                        stretch_effect = 'tempo %f' % time_factor
                    elif self.orchestra.speed_metaphor == Orchestra.PITCH:
                        stretch_effect = 'speed %f' % time_factor
                    self.orchestra.visualize(chunk, desired_duration, self.pan)

            if desired_time:
                self.logger.debug("at %f, playing %s at position %fs with duration %fs" % (
                        desired_time, filename, start_secs, length_secs))

            command = 'sox "%s" -t raw - channels 2 trim %f %f %s %s' % (
                filename, start_secs, length_secs,
                self._sox_mixer[file_info["num_channels"]], stretch_effect)
        return command

class NoisePlayer(Player):
    def get_command_for_sonic_interpretation(self, chunk, desired_time):
        if desired_time and self._previous_chunk_time:
            desired_duration = desired_time - self._previous_chunk_time
            fade_time = desired_duration/2
            command = 'sox -r %d -n -t raw -e signed -b 16 - synth %f whitenoise fade 0 %f %f channels 2 %s' % (
                Orchestra.SAMPLE_RATE, desired_duration,
                fade_time, fade_time,
                self._sox_mixer[2])
            return command


class Orchestra:
    SAMPLE_RATE = 44100
    MAX_GRAIN_DURATION = 0.5
    PLAYABLE_FORMATS = ['mp3', 'flac', 'wav']
    SUPPORTED_AUDIO_ENGINES = ['alsa', 'jack']
    STRETCH = 'stretch'
    PITCH = 'pitch'
    TRANSFERRED = 'transferred'
    NOISE = 'noise'

    _extension_re = re.compile('\.(\w+)$')

    def __init__(self, sessiondir, logger, tr_log,
                 realtime=False, timefactor=1,
                 resync_limit=None, quiet=False,
                 audio_engine='alsa', output_device='',
                 predecoded=False, file_location=None,
                 speed_metaphor=STRETCH,
                 visualizer_enabled=False,
                 content=TRANSFERRED):
        self.sessiondir = sessiondir
        self.logger = logger
        self.tr_log = tr_log
        self.realtime = realtime
        self.timefactor = timefactor
        self.resync_limit = resync_limit
        self.quiet = quiet
        self.audio_engine = audio_engine
        self.output_device = output_device
        self.predecoded = predecoded
        self.file_location = file_location
        self.speed_metaphor = speed_metaphor
        self.content = content

        self.gui = None
        self._check_which_files_are_audio()
        self._prepare_players()
        self._total_bytes = 0
        self._played_bytes = 0
        self._space = StereoSpace()
        self.stopwatch = Stopwatch()
        self.log_time_played_from = 0
        self.tr_log.flatten() # TODO: find better place for this call
        self.chunks = tr_log.chunks
        self._playing = False
        self.current_chunk_index = 0

        if visualizer_enabled:
            self.visualizer = liblo.Address(VISUALIZER_PORT)
        else:
            self.visualizer = None

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
        if self.content == Orchestra.TRANSFERRED:
            self._player_class = WavPlayer
            if self.predecoded:
                self._get_wav_files_info()
            else:
                raise Exception("playing wav without precoding is not supported")
        elif self.content == Orchestra.NOISE:
            self._player_class = NoisePlayer
        else:
            print "assuming MP3 content"
            self._player_class = MP3Player
            self._build_mpg123_options()
        self.players = []
        self._player_for_peer = dict()

    def _build_mpg123_options(self):
        self.mpg123_options = ""
        if self.quiet:
            self.mpg123_options += " -q"
        if self.resync_limit:
            self.mpg123_options += " --resync-limit %d" % self.resync_limit

    def _get_wav_files_info(self):
        for file_info in self.tr_log.files:
            file_info["duration"] = self._get_file_duration(file_info)
            file_info["num_channels"] = self._get_num_channels(file_info)
            self.logger.debug("duration for %r: %r\n" %
                              (file_info["name"], file_info["duration"]))

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
        return self.log_time_played_from + self.stopwatch.get_elapsed_time()

    def play_non_realtime(self):
        self.logger.debug("entering play_non_realtime")
        self._playing = True
        self.stopwatch.start()
        num_chunks = len(self.chunks)
        while self._playing and self.current_chunk_index < num_chunks:
            self.logger.debug("chunk index is %d" % self.current_chunk_index)
            chunk = self.chunks[self.current_chunk_index]
            self.handle_chunk(chunk)
            self.current_chunk_index += 1
        self.logger.debug("leaving play_non_realtime")

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
        player.play(chunk)

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
        player.play(chunk)
        
    def stop(self):
        self._playing = False
        self.log_time_played_from = self.get_current_log_time()
        self.stopwatch.stop()

    def handle_chunk(self, chunk):
        self.logger.debug("handling chunk %s" % chunk)
        chunk_start_time = chunk["t"]
        if self._chunk_is_audio(chunk):
            self.play_chunk(chunk, chunk_start_time)
        else:
            self.logger.debug("skipping non-audio chunk")

    def render(self, from_time=None, to_time=None):
        if from_time == None:
            from_time = 0
        if to_time == None:
            to_time = self.tr_log.lastchunktime() # TODO: add last chunk duration?
        duration = to_time - from_time
        output_buffer = AudioBuffer(self.SAMPLE_RATE, duration=duration)
        for chunk in self.chunks:
            if self._chunk_is_audio(chunk) and from_time <= chunk["t"] <= to_time:
                self._render_chunk(chunk, output_buffer, from_time)
        output_buffer.normalize()
        return output_buffer

    def _render_chunk(self, chunk, output_buffer, from_time):
        self.logger.debug("rendering chunk %s" % chunk)
        player = self.get_player_for_chunk(chunk)
        desired_time = chunk["t"] - from_time
        command = player.interpret_sonically(chunk, desired_time)
        if command:
            frames = AudioCommandReader(command,
                                        samplerate=self.SAMPLE_RATE,
                                        nchannels=2,
                                        samplesize=2).get_frames()
            chunk_buffer = AudioBuffer(self.SAMPLE_RATE, frames)
            self.logger.debug("actual duration: %f" % chunk_buffer.duration)
            output_buffer.mix(desired_time, chunk_buffer)

    def _chunk_is_audio(self, chunk):
        file_info = self.tr_log.files[chunk["filenum"]]
        return file_info["is_audio"]

    def play_chunk(self, chunk, chunk_start_time):
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
            self.logger.debug("playing chunk")
            player.play(chunk, now)
            self._played_bytes += chunk_size
        self._total_bytes += chunk_size
        self.logger.debug("recall rate: %f (%d/%d)" % (
                float(self._played_bytes) / self._total_bytes,
                self._played_bytes, self._total_bytes))

    def highlight_chunk(self, chunk):
        if self.gui:
            self.gui.highlight_chunk(chunk, True)
            threading.Timer(1.0,
                            self.gui.highlight_chunk, [chunk, False]).start()

    def visualize(self, chunk, duration, pan):
        if self.visualizer:
            angle = float(pan * 360)
            liblo.send(self.visualizer, "/chunk", chunk["end"]-chunk["begin"], duration, angle)

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
        pan = self._space.position_with_max_distance_to_nodes()
        self._space.add_node(pan)
        self.logger.debug("creating player number %d with pan %f" % (count, pan))
        return self._player_class(self, count, pan)

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

