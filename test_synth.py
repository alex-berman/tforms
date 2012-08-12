from synth_controller import SynthController
import time

DURATION = 13.83
synth = SynthController()
synth.load_sound(sound_id=1, filename="sonic-experiments/theme-nikolayeva-mono.wav")
sound = synth.start_playing(player_id=1, sound_id=1, position=0, pan=0.1)

start_time=time.time()
position = 0
while position < 1:
    position = (time.time() - start_time) / DURATION
    position = pow(position, .5)
    sound.set_cursor(position)
    time.sleep(.01)

sound.stop_playing()
