from synth_controller import SynthController
import time

synth = SynthController()
synth.load_sound(sound_id=1, filename="sonic-experiments/theme-nikolayeva-mono.wav")
player = synth.player()
sound = player.start_playing(sound_id=1, position=0, pan=0.5)
sound.play_to(target_position=0.5, desired_duration=2.0)
time.sleep(2.0)
sound.play_to(target_position=1.0, desired_duration=1.0)
time.sleep(1.0)
sound.stop_playing()
