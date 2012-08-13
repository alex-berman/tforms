import liblo
import threading
import time

PRECISION = .01
SUSTAIN = 1.0

class SynthControllerException(Exception):
    pass

class Player:
    def __init__(self, synth, id):
        self.synth = synth
        self.id = id
        self._target_position = None
        self._cursor = None
        self._desired_duration = None
        self._callbacks = []
        thread = threading.Thread(target=self._playback_thread)
        thread.daemon = True
        thread.start()

    def start_playing(self, sound_id, position, pan,
                      callback=None, callback_args=()):
        self.synth.log("Player(%s).start_playing(%s, %s, %s)" % (
                self.id, sound_id, position, pan))
        if self._desired_duration:
            raise SynthControllerException("trying to start new sound while already playing something")
        self.synth._send("/start", self.id, sound_id, position, pan)
        self._cursor = position
        if callback:
            self._callbacks.append((callback, callback_args))
        return Sound(self)

    def stop_playing(self):
        self.synth.log("Player(%s).stop_playing()" % self.id)
        self.synth._send("/stop", self.id)
        self._desired_duration = None
        self._fire_callbacks()

    def _fire_callbacks(self):
        for callback, args in self._callbacks:
            callback(*args)
        self._callbacks = []

    def play_to(self, target_position, desired_duration,
                callback=None, callback_args=()):
        self.synth.log("Player(%s).play_to(%s, %s)" % (
                self.id, target_position, desired_duration))
        self._fire_callbacks()
        if callback:
            self._callbacks.append((callback, callback_args))
        self._target_position = target_position
        self._start_time = time.time()
        self._start_position = self._cursor
        self._distance = target_position - self._start_position
        self._desired_duration = desired_duration

    def _playback_thread(self):
        while True:
            while self._desired_duration == None:
                time.sleep(PRECISION)

            position = self._start_position
            speed = None
            while self._desired_duration and self._elapsed_time() < self._desired_duration:
                remaining_time = self._desired_duration - self._elapsed_time()
                remaining_iterations = remaining_time / PRECISION
                remaining_distance = self._target_position - position
                target_speed = remaining_distance / remaining_iterations
                if speed == None:
                    speed = target_speed
                else:
                    speed += (target_speed - speed) * 0.05
                position += speed
                self.set_cursor(position)
                time.sleep(PRECISION)

            self._desired_duration = None
            self._start_time = time.time()
            while self._desired_duration == None and self._elapsed_time() < SUSTAIN:
                time.sleep(PRECISION)

            if self._desired_duration == None:
                self.stop_playing()

    def _elapsed_time(self):
        return time.time() - self._start_time

    def set_cursor(self, position):
        self.synth._send("/cursor", self.id, position)
        self._cursor = position

class Sound:
    def __init__(self, player):
        self.player = player

    def stop_playing(self):
        self.player.stop_playing()

    def play_to(self, target_position, desired_duration,
                callback=None, callback_args=()):
        self.player.play_to(target_position, desired_duration,
                            callback, callback_args)

class SynthController:
    PORT = 57120

    def __init__(self, logger=None):
        self.logger = logger
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()
        self._player_count = 1
        self._players = []

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def player(self):
        p = Player(self, self._new_player_id())
        self._players.append(p)
        return p

    def stop_all_players(self):
        for player in self._players:
            player.stop_playing()

    def _new_player_id(self):
        id = self._player_count
        self._player_count += 1
        return id

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        self.log("_send(%s, %s)" % (command, args))
        with self._lock:
            liblo.send(self.target, command, *args)

    def log(self, msg):
        if self.logger:
            self.logger.debug("SynthController.%s" % msg)
