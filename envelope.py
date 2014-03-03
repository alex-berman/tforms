class AdsrEnvelope:
    @staticmethod
    def from_string(string):
        attack, decay, sustain, slope = map(float, string.split(","))
        return AdsrEnvelope(attack, decay, sustain, slope)

    def __init__(self, attack=0, decay=0, sustain=1, slope=1):
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.slope = slope

    def value(self, t):
        if t < self.attack:
            return pow(t / self.attack, self.slope)
        elif self.decay == 0.0:
            return self.sustain
        elif t < (self.attack + self.decay):
            return 1.0 - (1.0 - self.sustain) * (t - self.attack) / self.decay
        else:
            return self.sustain
