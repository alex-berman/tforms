import osc
import socket
import threading
import struct

class Handler:
    def __init__(self, typespec, callback_func, user_data):
        self.typespec = typespec
        self.callback_func = callback_func
        self.user_data = user_data

class OscReceiver:
    def __init__(self, port=None, log_filename=None, proto=osc.TCP):
        if proto != osc.TCP:
            raise Exception("simple OSC receiver only supports TCP")
        if log_filename:
            raise Exception("log_filename not supported")
        if port is None:
            port = 0
        self._handlers = {}
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((socket.gethostbyname(socket.gethostname()), port))
        self._socket.listen(5)
        self.port = self._socket.getsockname()[1]
        self._queue = []
        self._lock = threading.Lock()

    def add_method(self, path, typespec, callback_func, user_data=None):
        self._handlers[path] = Handler(typespec, callback_func, user_data)

    def start(self):
        serve_thread = threading.Thread(target=self._serve)
        serve_thread.daemon = True
        serve_thread.start()

    def _serve(self):
        client_socket, client_address = self._socket.accept()
        self._client_socket_file = client_socket.makefile("rb")
        while True:
            self._serve_once()

    def _serve_once(self):
        size_int32 = self._client_socket_file.read(4)
        size = struct.unpack(">i", size_int32)[0]
        self._data = self._client_socket_file.read(size)
        address_pattern = self._consume_osc_string()
        assert address_pattern.startswith("/")

        try:
            handler = self._handlers[address_pattern]
        except KeyError:
            raise Exception("unhandled address: %s" % address_pattern)

        comma_prefixed_type_tag_string = self._consume_osc_string()
        assert comma_prefixed_type_tag_string.startswith(",")
        type_tag_string = comma_prefixed_type_tag_string[1:]
        if handler.typespec != type_tag_string:
            raise Exception("type tag mismatch")

        args = []
        type_tags = list(type_tag_string)
        for type_tag in type_tags:
            arg = self._read_arg(type_tag)
            args.append(arg)

        src = None
        with self._lock:
            self._queue.append((address_pattern, args, type_tags, src,
                                handler.callback_func, handler.user_data))

    def _read_arg(self, type_tag):
        if type_tag == 'i':
            return self._consume_int32()
        elif type_tag == 'f':
            return self._consume_float32()
        elif type_tag == 's':
            return self._consume_osc_string()
        else:
            raise Exception("unsupported type tag %s" % type_tag)

    def _consume_int32(self):
        int32 = self._data[0:4]
        value = struct.unpack(">i", int32)[0]
        self._data = self._data[4:]
        return value

    def _consume_float32(self):
        int32 = self._data[0:4]
        value = struct.unpack(">f", int32)[0]
        self._data = self._data[4:]
        return value
        
    def _consume_osc_string(self):
        terminated = False
        num_string_bytes = 0
        result = ""
        chars = list(self._data)
        while not (terminated and (num_string_bytes % 4) == 0):
            c = chars.pop(0)
            if c == '\0':
                terminated = True
            else:
                result += c
            num_string_bytes += 1
        self._data = self._data[num_string_bytes:]
        return result

    def serve(self):
        with self._lock:
            for path, args, types, src, callback_func, user_data in self._queue:
                self._fire_callback_with_exception_handler(
                    path, args, types, src, callback_func, user_data)
            self._queue = []

    def _fire_callback_with_exception_handler(self, path, args, types, src, callback, user_data):
        try:
            callback(path, args, types, src, user_data)
        except Exception as err:
            traceback_printer.print_traceback()
            raise err
