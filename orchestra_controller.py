import liblo
import orchestra

class OrchestraController:
    def __init__(self):
        self.target = liblo.Address(orchestra.PORT)

    def visualizing_segment(self, segment_id, pan):
        self._send("/visualizing", segment_id, pan)

    def _send(self, command, *args):
        liblo.send(self.target, command, *args)
