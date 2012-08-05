import liblo
import pickle

class OscReceiver(liblo.Server):
    def __init__(self, port, log_filename=None):
        liblo.Server.__init__(self, port)
        if log_filename:
            self.read_log(log_filename)
            self.log = True
            self.sender = liblo.Address(port)
        else:
            self.log = False

    def serve(self):
        while self.recv(0.01):
            pass

    def read_log(self, filename):
        f = open(filename, "r")
        self.entries = []
        try:
            while True:
                entry = pickle.load(f)
                self.entries.append(entry)
        except EOFError:
            pass
        f.close()

    def serve_from_log_until(self, time_target):
        while True:
            if len(self.entries) == 0:
                return
            (t, args) = self.entries[0]
            if t < time_target:
                liblo.send(self.sender, *args)
                self.entries.pop(0)
                self.serve()
            else:
                return
