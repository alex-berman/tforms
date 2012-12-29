import liblo
import pickle
import time
import threading

class OscSender:
    def __init__(self, port, host=None, log_filename=None):
        if host is None:
            host = "localhost"
        self._lock = threading.Lock()
        self.address = liblo.Address(host, port, liblo.TCP)
        if log_filename:
            self.log = open(log_filename, "w")
            self.start_time = time.time()
        else:
            self.log = None

    def send(self, *args):
        with self._lock:
            liblo.send(self.address, *args)
        if self.log:
            t = time.time() - self.start_time
            self.log.write(pickle.dumps((t, args)))
