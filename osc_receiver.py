import liblo
import pickle
import traceback, sys
import threading

class OscReceiver(liblo.Server):
    def __init__(self, port, log_filename=None):
        liblo.Server.__init__(self, port)
        if log_filename:
            self.read_log(log_filename)
            self.log = True
            self.sender = liblo.Address(port)
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
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print >> sys.stderr, "".join(traceback.format_exception(exc_type, exc_value,
                                                                    exc_traceback))            
            raise err



