import liblo
import threading

class Sound:
    def __init__(self, synth, player_id, sound_id, position, pan):
        self.synth = synth
        self.player_id = player_id
        self.synth._send("/start", player_id, sound_id, position, pan)
        self.cursor = position

    def stop_playing(self):
        self.synth._send("/stop", self.player_id)

    def set_cursor(self, position):
        self.synth._send("/cursor", self.player_id, position)
        self.cursor = position

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def start_playing(self, player_id, sound_id, position, pan):
        return Sound(self, player_id, sound_id, position, pan)

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
