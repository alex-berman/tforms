import liblo
import threading

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def start_playing(self, player_id, sound_id, position, pan):
        self._send("/start", player_id, sound_id, position, pan)

    def stop_playing(self, player_id):
        self._send("/stop", player_id)

    def set_cursor(self, player_id, position):
        self._send("/cursor", player_id, position)

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
