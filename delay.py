import numpy as np

from module import Module

# TODO: Modulated delay line
# (Right now, this is just an echo, though the user can manually change the delay.)
class Delay(Module):
    def __init__(self, sample_rate, duration, delay, feedback=0.1):
        super().__init__(sample_rate)
        self.buffer = np.zeros(int(duration * sample_rate))
        self.delay = delay
        self.feedback = feedback
        self.buffer_index = 0
    
    def process(self, input_buffer, output_buffer):
        buffer, buffer_index, feedback = self.buffer, self.buffer_index, self.feedback
        # TODO: Allow fractional delay
        delay = int(self.delay * self.sample_rate)
        for i in range(len(input_buffer)):
            out = buffer[(buffer_index - delay) % len(buffer)]
            buffer[buffer_index] = (1 - feedback) * input_buffer[i] + feedback * out
            output_buffer[i] = out
            buffer_index += 1
            if buffer_index >= len(buffer):
                buffer_index %= len(buffer)
        self.buffer_index = buffer_index