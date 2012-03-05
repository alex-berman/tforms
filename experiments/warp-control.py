import liblo
import random
import time

PORT = 57120
target = liblo.Address(PORT)

sounds = ["theme-acad-st-martin-mono.wav",
          "theme-nikolayeva-mono.wav",
          ]

for i in range(len(sounds)):
    sound = sounds[i]
    liblo.send(target, "/load", i, sound)

while True:
    sound_id = random.randint(0, len(sounds) - 1)
    begin = 0
    end = 1
    duration = random.uniform(1.0, 15.0)
    print sounds[sound_id]
    liblo.send(target, "/play", sound_id, begin, end, duration)
    pause = random.uniform(1.0, 2.0)
    time.sleep(pause)

