import random
from vector import Vector2d

def spring_force(source, target, desired_distance):
    d = target - source
    distance = d.mag()
    if distance == 0:
        result = Vector2d(random.uniform(0.0, 0.1),
                          random.uniform(0.0, 0.1))
    else:
        result = d - d * desired_distance / distance
    return result
