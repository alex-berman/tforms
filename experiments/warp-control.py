import liblo

PORT = 57120
target = liblo.Address(PORT)

sound_id = 0
liblo.send(target, "/play", sound_id, 0.0, 1.0, 15)

