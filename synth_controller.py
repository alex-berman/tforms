import liblo
import threading
from osc_receiver import OscReceiver
import time

class SynthController:
    PORT = 57120

    def __init__(self):
        self.target = liblo.Address(self.PORT)
        self._lock = threading.Lock()
        self._load_results = {}
        self._sc_listener = OscReceiver(proto=liblo.UDP)
        self._sc_listener.add_method("/loaded", "ii", self._handle_loaded)
        self._sc_listener.start()
        self._send("/info_subscribe", self._sc_listener.port)

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)
        num_frames_loaded = self._get_load_result(sound_id)
        if num_frames_loaded <= 0:
            raise Exception("error when loading sound %s: SC reports numFrames=%s" % (
                    filename, num_frames_loaded))
        return num_frames_loaded

    def _get_load_result(self, sound_id):
        while True:
            if sound_id in self._load_results:
                result = self._load_results[sound_id]
                del self._load_results[sound_id]
                return result
            self._sc_listener.serve()
            time.sleep(0.01)

    def _handle_loaded(self,path, args, types, src, data):
        sound_id, result = args
        self._load_results[sound_id] = result

    def free_sound(self, sound_id):
        self._send("/free", sound_id)

    def free_sounds(self):
        self._send("/free_all")

    def play_segment(self, segment_id, sound_id, begin, end, period_duration, looped_duration, channel, pan):
        if looped_duration:
            self._send("/loop", segment_id, sound_id, begin, end, period_duration, looped_duration, channel, pan)
        else:
            self._send("/play", segment_id, sound_id, begin, end, period_duration, channel, pan)

    def pan(self, segment_id, pan):
        self._send("/pan", segment_id, pan)

    def stop_all(self):
        self._send("/stop_all")

    def sync_beep(self):
        self._send("/sync_beep")

    def subscribe_to_amp(self, port):
        self._send("/amp_subscribe", port)

    def subscribe_to_waveform(self, port):
        self._send("/waveform_subscribe", port)

    def _send(self, command, *args):
        with self._lock:
            liblo.send(self.target, command, *args)
