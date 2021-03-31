import numpy as np

class ExampleModule:
    "Just an example; generates a sine wave."

    def __init__(self, sample_rate, freq=440):
        # Set any initial state here.
        self.sample_rate = sample_rate
        self.freq = freq
        self.phase = 0

    def process(self, output_buffer):
        # Fill the output buffer with samples.
        # Note that other modules (such as filters) will also take an input_buffer of samples to process.
        output_buffer[:,0] = np.sin(2*np.pi*self.freq*np.arange(len(output_buffer))/self.sample_rate + self.phase)
        # Update state as needed.
        self.phase += 2*np.pi*self.freq*len(output_buffer)/self.sample_rate
        self.phase %= 2*np.pi

