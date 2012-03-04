import liblo
import time

PORT = 57120
target = liblo.Address(PORT)

t0 = time.time()
while True:
    t = time.time()
    liblo.send(target, "/cursor", (t % 3.0) / 3.0)
    time.sleep(0.1)
