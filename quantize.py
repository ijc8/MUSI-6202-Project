import numpy as np

from module import Module

class Quantizer(Module):

    PARAMETERS = ("depth", "dither", "mix")

    def __init__(self, depth=16, dither='triangular'):
        super().__init__(None)  # NOTE: Sample rate is irrelevant for this module.
        self.depth = depth
        self.dither = dither

    def process(self, input_buffer, output_buffer):
        buf = input_buffer * 2**self.depth
        if self.dither == 'triangular':
            buf += np.random.triangular(-1, 0, 1)
        elif self.dither == 'rectangular':
            buf += np.random.uniform(-1, 1)
        output_buffer[:] = np.round(buf) / 2**self.depth