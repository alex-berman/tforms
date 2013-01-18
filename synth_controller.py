import liblo
import threading
from osc_receiver import OscReceiver
import time
import subprocess
import re

class SynthController:
    DEFAULT_PORT = 57120

    def __init__(self):
        self._sc_process = None

    def launch_engine(self, mode):
        self.kill_engine()

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
        self._engine_running = True
        self.lang_port = None
        initialized = False
        while self.lang_port is None or not initialized:
            line = self._sc_process.stdout.readline().strip()
            print "SC: %s" % line
            m = re.search('langPort=(\d+)', line)
            if m:
                self.lang_port = int(m.group(1))
            elif line == "Receiving notification messages from server localhost":
                initialized = True
        self._sc_output_thread = threading.Thread(target=self._read_sc_output)
        self._sc_output_thread.daemon = True
        self._sc_output_thread.start()

    def _read_sc_output(self):
        while self._engine_running:
            line = self._sc_process.stdout.readline()
            if line:
                print "SC: %s" % line,

    def connect(self, port):
        self._lock = threading.Lock()
        self.target = liblo.Address(port)

    def subscribe_to_info(self):
        self._load_results = {}
        self._sc_listener = OscReceiver(proto=liblo.TCP)
        self._sc_listener.add_method("/loaded", "ii", self._handle_loaded)
        self._sc_listener.start()
        self._send("/info_subscribe", self._sc_listener.port)

    def kill_engine(self):
        if self._sc_process:
            self._engine_running = False
            self._sc_process.kill()
            self._sc_process = None
        subprocess.call("killall sclang", shell=True)
        subprocess.call("killall scsynth", shell=True)

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
