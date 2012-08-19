import liblo
import threading

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def play_segment(self, sound_id, begin, end, duration, pan):
        self._send("/play", sound_id, begin, end, duration, pan)

    def pan(self, sound_id, pan):
        self._send("/pan", sound_id, pan)

    def stop_all(self):
        self._send("/stop_all")

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
