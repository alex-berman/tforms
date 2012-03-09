import liblo
import threading

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def play_chunk(self, sound_id, begin, end, duration, pan):
        self._send("/play", sound_id, begin, end, duration, pan)

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
