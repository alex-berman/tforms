import liblo
import pickle
import threading
import traceback_printer

class OscReceiver(liblo.Server):
    def __init__(self, port=None, log_filename=None):
        liblo.Server.__init__(self, port, liblo.TCP)
        if log_filename:
            self.read_log(log_filename)
            self.log = True
            self.sender = liblo.Address("localhost", self.port, liblo.TCP)
        else:
            self.log = False
            self._queue = []
            self._lock = threading.Lock()

    def add_method(self, path, typespec, callback_func):
        liblo.Server.add_method(self, path, typespec, self._callback, callback_func)

    def _callback(self, path, args, types, src, callback_func):
        with self._lock:
            self._queue.append((path, args, types, src, callback_func))

    def start(self):
        if not self.log:
            serve_thread = threading.Thread(target=self._serve)
            serve_thread.daemon = True
            serve_thread.start()

    def _serve(self):
        while True:
            self.recv()

    def serve(self):
        with self._lock:
            for path, args, types, src, callback_func in self._queue:
                self._fire_callback_with_exception_handler(
                    path, args, types, src, callback_func)
            self._queue = []

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

    def _fire_callback_with_exception_handler(self, path, args, types, src, callback):
        data = None
        try:
            callback(path, args, types, src, data)
        except Exception as err:
            traceback_printer.print_traceback()
            raise err
