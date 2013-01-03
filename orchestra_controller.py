import osc
import osc_sender
import orchestra

class OrchestraController(osc_sender.OscSender):
    def __init__(self, host, port):
        osc_sender.OscSender.__init__(self, port, host)

    def register(self, port):
        self.send("/register", port)

    def visualizing_segment(self, segment_id):
        self.send("/visualizing", segment_id)

    def set_listener_position(self, x, y):
        self.send("/set_listener_position", x, y)

    def set_listener_orientation(self, orientation):
        self.send("/set_listener_orientation", orientation)

    def place_segment(self, segment_id, x, y, duration):
        self.send("/place_segment", segment_id, x, y, duration)

    def enable_smooth_movement(self):
        self.send("/enable_smooth_movement")

    def start_segment_movement_from_peer(self, segment_id, duration):
        self.send("/start_segment_movement_from_peer", segment_id, duration)
