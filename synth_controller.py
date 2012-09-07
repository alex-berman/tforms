import liblo
import threading

class SynthController:
    PORT = 57121

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)

    def play_segment(self, segment_id, sound_id, begin, end, duration, channel):
        self._send("/play", segment_id, sound_id, begin, end, duration, channel)

    def pan(self, segment_id, pan):
        self._send("/pan", segment_id, pan)

    def stop_all(self):
        self._send("/stop_all")

    def sync_beep(self):
        self._send("/sync_beep")

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
