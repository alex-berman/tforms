import math

def sigmoid(v):
    return 1.0 / (1.0 + math.exp((-v + .5) * 20))
