import numpy as np
from module import Module

class ExampleModule(Module):
    "Just an example; generates a sine wave."

    def __init__(self, sample_rate, freq=440):
        super().__init__(sample_rate)
        # Set any initial state here.
        self.freq = freq
        self.phase = 0

    def process(self, input_buffer, output_buffer):
        # Fill the output buffer with samples.
        # Note that other modules (such as filters) will also take an input_buffer of samples to process.
        output_buffer[:,0] = np.sin(2*np.pi*self.freq*np.arange(len(output_buffer))/self.sample_rate + self.phase)
        # Update state as needed.
        self.phase += 2*np.pi*self.freq*len(output_buffer)/self.sample_rate
        self.phase %= 2*np.pi

