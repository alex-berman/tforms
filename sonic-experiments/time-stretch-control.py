import liblo
import time

PORT = 57120
target = liblo.Address(PORT)
player_id = 0

factor = 5.0
t0 = time.time()
while True:
    t = time.time()
    liblo.send(target, "/cursor", player_id, (t % factor) / factor)
    time.sleep(0.01)
