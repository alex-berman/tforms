from synth_controller import SynthController, SynthControllerException
import time
import unittest

synth = SynthController()
synth.load_sound(sound_id=1, filename="sonic-experiments/theme-nikolayeva-mono.wav")
synth.load_sound(sound_id=2, filename="sonic-experiments/theme-acad-st-martin-mono.wav")

class SynthControllerTest(unittest.TestCase):
    def test_play_sound_with_different_speeds(self):
        player = synth.player()
        sound = player.start_playing(sound_id=1, position=0, pan=0.5)
        sound.play_to(target_position=0.5, desired_duration=2.0)
        time.sleep(2.0)
        sound.play_to(target_position=1.0, desired_duration=1.0)
        time.sleep(1.0)
        sound.stop_playing()

    def test_trying_to_play_two_sounds_simultaneously_with_same_player_raises_exception(self):
        player = synth.player()
        sound1 = player.start_playing(sound_id=1, position=0, pan=0.5)
        sound1.play_to(target_position=0.5, desired_duration=2.0)
        with self.assertRaises(SynthControllerException):
            sound2 = player.start_playing(sound_id=2, position=0, pan=0.5)

    def test_automatic_stop(self):
        player = synth.player()
        sound = player.start_playing(sound_id=1, position=0, pan=0.5)
        sound.play_to(target_position=0.5, desired_duration=2.0)
        time.sleep(5.0)

    def test_two_players(self):
        player1 = synth.player()
        sound1 = player1.start_playing(sound_id=1, position=0, pan=0)
        sound1.play_to(target_position=1.0, desired_duration=3.0)
        time.sleep(1.5)
        player2 = synth.player()
        sound2 = player2.start_playing(sound_id=2, position=0, pan=1)
        sound2.play_to(target_position=1.0, desired_duration=3.0)
        time.sleep(3.0)
        sound1.stop_playing()
        sound2.stop_playing()
