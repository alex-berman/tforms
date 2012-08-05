import liblo
import pickle
import time

class OscSender:
    def __init__(self, port, log_filename=None):
        self.address = liblo.Address(port)
        if log_filename:
            self.log = open(log_filename, "w")
            self.start_time = time.time()
        else:
            self.log = None

    def send(self, *args):
        liblo.send(self.address, *args)
        if self.log:
            t = time.time() - self.start_time
            self.log.write(pickle.dumps((t, args)))
