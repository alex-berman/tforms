import liblo
import threading
import time

PRECISION = .01

class Player:
    def __init__(self, synth, player_id):
        self.synth = synth
        self.player_id = player_id

    def start_playing(self, sound_id, position, pan):
        return Sound(self.synth, self.player_id, sound_id, position, pan)

class Sound:
    def __init__(self, synth, player_id, sound_id, position, pan):
        self.synth = synth
        self.player_id = player_id
        self.synth._send("/start", player_id, sound_id, position, pan)
        self.cursor = position

    def stop_playing(self):
        self.synth._send("/stop", self.player_id)

    def play_to(self, target_position, desired_duration):
        thread = threading.Thread(target=self._play_to,
                                  args=(target_position, desired_duration))
        thread.daemon = True
        thread.start()

    def _play_to(self, target_position, desired_duration):
        self._start_time = time.time()
        start_position = self.cursor
        distance = target_position - start_position
        while self.elapsed_time() < desired_duration:
            position = start_position + self.elapsed_time() / desired_duration * distance
            self.set_cursor(position)
            time.sleep(PRECISION)

    def elapsed_time(self):
        return time.time() - self._start_time

    def set_cursor(self, position):
        self.synth._send("/cursor", self.player_id, position)
        self.cursor = position

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()
        self._player_count = 1

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def player(self):
        return Player(self, self._new_player_id())

    def _new_player_id(self):
        id = self._player_count
        self._player_count += 1
        return id

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
