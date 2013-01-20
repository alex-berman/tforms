import collections
import random

class Shuffler:
    def __init__(self, choices, min_dist=None):
        if min_dist is None:
            min_dist = len(choices) / 2
        self.choices = set(choices)
        self.last_choices = collections.deque(maxlen=min_dist)

    def next(self):
        c = random.choice(list(self.choices - set(self.last_choices)))
        self.last_choices.append(c)
        return c

# shuffler = Shuffler(range(10))
# while True:
#     print shuffler.next()
