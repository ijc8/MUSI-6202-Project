import numpy as np

from module import Module


class Tremolo(Module):

    PARAMETERS = ("rate", "amp", "mix")

    def __init__(self, sample_rate, rate=8, amp=0.73):
        super().__init__(sample_rate)
        self.rate = rate
        self.amp = amp
        self.phase = 0

    def process(self, input_buffer, output_buffer):
        t = np.arange(len(input_buffer))/self.sample_rate
        # Amplitude varies from (1 - amp) to 1.
        amp = np.sin(2*np.pi*self.rate*t + self.phase) * self.amp / 2 + (1 - self.amp / 2)
        output_buffer[:] = input_buffer * amp
        self.phase = (self.phase + 2*np.pi*self.rate*len(input_buffer)/self.sample_rate) % (2*np.pi)