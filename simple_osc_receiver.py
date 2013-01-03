import osc
import socket
import threading

CRLF = "\r\n"

class OscReceiver:
    def __init__(self, port=0, log_filename=None, proto=osc.TCP):
        if proto != osc.TCP:
            raise Exception("simple OSC receiver only supports TCP")
        if log_filename:
            raise Exception("log_filename not supported")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("localhost", port))
        self._socket.listen(5)
        self.port = self._socket.getsockname()[1]

    def add_method(self, path, typespec, callback_func, user_data=None):
        pass

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
        line = self._readline()
        print line

    def _readline(self):
        s = self._client_socket_file.readline()
        if not s:
            raise EOFError
        if s[-2:] == CRLF:
            s = s[:-2]
        elif s[-1:] in CRLF:
            s = s[:-1]
        return s

    def serve(self):
        pass
