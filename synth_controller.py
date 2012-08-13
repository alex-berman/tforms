import liblo
import threading
import time
import Queue

PRECISION = .0001
SUSTAIN = 1.0

START = "START"
STOP = "STOP"
TARGET_POSITION = "TARGET_POSITION"

LINEAR_STRATEGY, SMOOTH_STRATEGY = range(2)
STRATEGY = LINEAR_STRATEGY
#STRATEGY = SMOOTH_STRATEGY

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
        self._queue = Queue.Queue()
        thread = threading.Thread(target=self._playback_thread)
        thread.daemon = True
        thread.start()

    def start_playing(self, sound_id, position, pan,
                      callback=None, callback_args=()):
        self.synth.log("Player(%s).start_playing(%s, %s, %s)" % (
                self.id, sound_id, position, pan))
        self._queue.put((START,
                         (sound_id, position, pan, callback, callback_args)))
        return Sound(self)

    def stop_playing(self):
        self.synth.log("Player(%s).stop_playing()" % self.id)
        self._queue.put((STOP, ()))

    def play_to(self, target_position, desired_duration,
                callback=None, callback_args=()):
        self.synth.log("Player(%s).play_to(%s, %s)" % (
                self.id, target_position, desired_duration))
        self._queue.put((TARGET_POSITION, (
                    target_position, desired_duration,
                    callback, callback_args)))

    def _playback_thread(self):
        while True:
            self._await_start()
            self._stopped = False
            self._timed_out = False
            while not self._stopped and not self._timed_out:
                self.synth.log("_stopped=%s _timed_out=%s" % (self._stopped, self._timed_out))
                self._await_target_position_or_stopped_or_timeout()
                if not self._stopped and not self._timed_out:
                    self._move_cursor_until_target_position_reached_or_stopped_or_new_target_position()
            self._fire_callbacks()

    def _await_start(self):
        self.synth.log("_await_start")
        started = False
        while not started:
            message = self._get_message()
            command = message[0]
            if command == START:
                self._handle_start(message[1])
                started = True
            elif command == TARGET_POSITION:
                self._handle_target_position_as_start(message[1])
                started = True
            elif command == STOP:
                pass
            else:
                self.synth.raise_exception(
                    "expected START, STOP or TARGET_POSITION but got %s" % str(message))

    def _handle_start(self, args):
        (self._sound_id, self._cursor, self._pan, callback, callback_args) = args
        if callback:
            self._callbacks.append((callback, callback_args))
        self.synth._send("/start", self.id, self._sound_id, self._cursor, self._pan)
        
    def _await_target_position_or_stopped_or_timeout(self):
        self.synth.log("_await_target_position_or_stopped_or_timeout")
        try:
            message = self._get_message(SUSTAIN)
            command, args = message
            if command == TARGET_POSITION:
                self._handle_target_position(args)
            elif command == STOP:
                self._handle_stop()
            else:
                self.synth.raise_exception("expected TARGET_POSITION or STOP but got %s" % str(message))
        except Queue.Empty:
            self.synth.log("timed out")
            self.synth._send("/stop", self.id)
            self._timed_out = True

    def _move_cursor_until_target_position_reached_or_stopped_or_new_target_position(self):
        self.synth.log("_move_cursor_until_target_position_reached_or_stopped_or_new_target_position")
        if STRATEGY == SMOOTH_STRATEGY:
            position = self._start_position
        speed = None
        while True:
            remaining_time = self._desired_duration - self._elapsed_time()
            if remaining_time <= 0:
                return
            desired_position = self._start_position + self._distance * self._elapsed_time() / self._desired_duration
            if STRATEGY == LINEAR_STRATEGY:
                position = desired_position
            elif STRATEGY == SMOOTH_STRATEGY:
                target_speed = desired_position - position
                if speed == None:
                    speed = target_speed
                else:
                    speed += (target_speed - speed) * PRECISION * 5
                position += speed
            self.set_cursor(position)
            try:
                message = self._get_message(PRECISION)
                command, args = message
                if command == STOP:
                    self._handle_stop()
                    return
                elif command == TARGET_POSITION:
                    self._handle_target_position(args)
                else:
                    self.synth.raise_exception(
                        "expected STOP or TARGET_POSITION or nothing but got %s" % str(message))
            except Queue.Empty:
                pass

    def _handle_target_position(self, args):
        (self._target_position, self._desired_duration, callback, callback_args) = args
        self._fire_callbacks()
        if callback:
            self._callbacks.append((callback, callback_args))
        self._start_time = time.time()
        self._start_position = self._cursor
        self._distance = self._target_position - self._start_position

    def _handle_target_position_as_start(self, args):
        (self._target_position, self._desired_duration, callback, callback_args) = args
        self._handle_start((self._sound_id, self._target_position, self._pan,
                            callback, callback_args))

    def _handle_stop(self):
        if not self._stopped:
            self.synth._send("/stop", self.id)
            self._stopped = True

    def _fire_callbacks(self):
        for callback, args in self._callbacks:
            callback(*args)
        self._callbacks = []

    def _elapsed_time(self):
        return time.time() - self._start_time

    def set_cursor(self, position):
        self.synth._send("/cursor", self.id, position)
        self._cursor = position

    def _get_message(self, timeout=None):
        message = self._queue.get(True, timeout)
        self.synth.log("processing message %s" % str(message))
        return message

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
            self.logger.debug("SynthController: %s" % msg)

    def raise_exception(self, msg):
        self.log("raise_exception(%s)" % msg)
        raise SynthControllerException(msg)

    def shutdown(self):
        time.sleep(SUSTAIN + 0.1)
