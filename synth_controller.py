import liblo
import threading
from osc_receiver import OscReceiver
import time
import subprocess
import re

class SynthController:
    PORT = 57120

    def launch_engine(self, mode):
        f = open("sc/engine.sc")
        engine = f.read()
        f.close()

        f = open("sc/%s.sc" % mode)
        engine += f.read()
        f.close()

        out = open("sc/_compiled.sc", "w")

        f = open("sc/boot.sc")
        for line in f:
            line = line.replace("//$ENGINE", engine)
            print >>out, line,
        f.close()

        out.close()

        self._sc_process = subprocess.Popen("sclang sc/_compiled.sc", shell=True,
                                            stdout=subprocess.PIPE)
        lang_port = None
        initialized = False
        while lang_port is None or not initialized:
            line = self._sc_process.stdout.readline().strip()
            print "SC: %s" % line
            m = re.search('langPort=(\d+)', line)
            if m:
                lang_port = int(m.group(1))
                if lang_port != self.PORT:
                    self.kill_engine()
                    raise Exception("expected SC langPort to be %s but it says %s" % (
                            self.PORT, lang_port))
            elif line == "Shared memory server interface initialized":
                initialized = True

    def connect(self):
        self._lock = threading.Lock()
        self._load_results = {}
        self._sc_listener = OscReceiver(proto=liblo.TCP)
        self._sc_listener.add_method("/loaded", "ii", self._handle_loaded)
        self._sc_listener.start()
        self.target = liblo.Address(self.PORT)
        self._send("/info_subscribe", self._sc_listener.port)

    def kill_engine(self):
        self._sc_process.kill()
        subprocess.call("killall sclang", shell=True)
        subprocess.call("killall scsynth", shell=True)
        time.sleep(1.0) # time to release langPort

    def load_sound(self, sound_id, filename):
        self._send("/load", sound_id, filename)
        num_frames_loaded = self._get_load_result(sound_id)
        return num_frames_loaded

    def _get_load_result(self, sound_id, timeout=10.0):
        t = time.time()
        while True:
            if sound_id in self._load_results:
                result = self._load_results[sound_id]
                del self._load_results[sound_id]
                return result
            elif (time.time() - t) > timeout:
                return None
            else:
                self._sc_listener.serve()
                time.sleep(0.01)

    def _handle_loaded(self,path, args, types, src, data):
        sound_id, result = args
        print "got /loaded %s" % args #TEMP
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
