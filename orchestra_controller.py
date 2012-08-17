import liblo
import orchestra

class OrchestraController:
    def __init__(self):
        self.target = liblo.Address(orchestra.PORT)

    def visualizing_chunk(self, chunk_id, pan):
        self._send("/visualizing", chunk_id, pan)

    def _send(self, command, *args):
        liblo.send(self.target, command, *args)
