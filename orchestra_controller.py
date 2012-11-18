import liblo
import orchestra

class OrchestraController:
    def __init__(self):
        self.target = liblo.Address(orchestra.PORT)

    def register(self):
        self._send("/register")

    def visualizing_segment(self, segment_id):
        self._send("/visualizing", segment_id)

    def set_listener_position(self, x, y):
        self._send("/set_listener_position", x, y)

    def set_listener_orientation(self, orientation):
        self._send("/set_listener_orientation", orientation)

    def place_segment(self, segment_id, x, y, duration):
        self._send("/place_segment", segment_id, x, y, duration)

    def _send(self, command, *args):
        liblo.send(self.target, command, *args)
