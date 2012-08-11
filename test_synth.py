from synth_controller import SynthController
import time

DURATION = 13.83
s = SynthController()
s.load_sound(sound_id=1, filename="sonic-experiments/theme-nikolayeva-mono.wav")
s.start_playing(player_id=1, sound_id=1, position=0, pan=0.5)

start_time=time.time()
position = 0
while position < 1:
    position = (time.time() - start_time) / DURATION
    position = pow(position, .5)
    s.set_cursor(player_id=1, position=position)
    time.sleep(.01)

s.stop_playing(player_id=1)
