import liblo
import time

PORT = 57120
target = liblo.Address(PORT)

factor = 15.0
t0 = time.time()
while True:
    t = time.time()
    liblo.send(target, "/cursor", (t % factor) / factor)
    time.sleep(0.01)
