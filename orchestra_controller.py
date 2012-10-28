import liblo
import orchestra

class OrchestraController:
    def __init__(self):
        self.target = liblo.Address(orchestra.PORT)

    def register(self):
        self._send("/register")

    def visualizing_segment(self, segment_id, channel):
        self._send("/visualizing", segment_id, channel)

    def _send(self, command, *args):
        liblo.send(self.target, command, *args)
