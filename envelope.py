from module import Module


class Envelope(Module):
    "Simple Attack/Decay Envelope"

    def __init__(self, sample_rate, attack=0.01, decay=0.3):
        super().__init__(sample_rate)
        self.attack = attack
        self.decay = decay
        self.triggered = False
        self.velocity = 0
        self.amp = 0

    def trigger(self, velocity):
        self.triggered = True
        self.velocity = velocity    

    def process(self, input_buffer, output_buffer):
        amp = self.amp
        attack = self.attack * self.sample_rate
        decay = self.decay * self.sample_rate
        for i in range(len(input_buffer)):
            if self.triggered:
                if amp < self.velocity / 127:
                    amp += self.velocity / 127 / attack
                    if amp > self.velocity / 127:
                        amp = self.velocity / 127
                else:
                    self.triggered = False
            else:
                if amp > 0:
                    amp -= self.velocity / 127 / decay
                if amp < 0:
                    amp = 0
            output_buffer[i] = input_buffer[i] * amp
        self.amp = amp