import liblo
import time
import threading

class OscSender:
    def __init__(self, port, host=None):
        if host is None:
            host = "localhost"
        self._lock = threading.Lock()
        self.address = liblo.Address(host, port, liblo.TCP)

    def send(self, *args):
        with self._lock:
            liblo.send(self.address, *args)
