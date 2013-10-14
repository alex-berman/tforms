import cPickle

class MessageLogWriter:
    def __init__(self, filename):
        self._file = open(filename, "w")

    def write(self, t, handler_name, args):
        self._file.write(cPickle.dumps((t, handler_name, args)))

class MessageLogReader:
    def __init__(self, filename):
        self._read_log(filename)

    def _read_log(self, filename):
        f = open(filename, "r")
        self._entries = []
        try:
            while True:
                entry = cPickle.load(f)
                self._entries.append(entry)
        except EOFError:
            pass
        f.close()

    def read_until(self, time_target):
        result = []
        while True:
            if len(self._entries) == 0:
                return result
            (t, handler_name, args) = self._entries[0]
            if t < time_target:
                result.append((t, handler_name, args))
                self._entries.pop(0)
            else:
                return result

