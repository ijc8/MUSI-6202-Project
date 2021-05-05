import numpy as np
from scipy import signal

from module import Module
import utility


class ShortConvolver(Module):
    "Short convolution, for impulse responses shorter than the block size."

    def __init__(self, sample_rate, impulse_response):
        super().__init__(sample_rate)
        self.impulse_response = impulse_response
        self.history = np.zeros(len(impulse_response) - 1)

    def process(self, input_buffer, output_buffer):
        buffer_with_history = np.concatenate((self.history, input_buffer))
        # NOTE: The order is important here, since output_buffer refer to the same memory as input_buffer.
        self.history[:] = input_buffer[-len(self.history):]
        output_buffer[:] = np.convolve(buffer_with_history, self.impulse_response, mode='valid')
 

class ConvolutionFilter(Module):
    "Filter audio by convolving with Parks-McClellan/Remez exchange algorithm-designed FIR."

    def __init__(self, sample_rate, order=28, freq=1000, bandwidth=400, transition_width=300, type="bpf"):
        super().__init__(sample_rate)
        self._order = order
        self._freq = freq
        self._bandwidth = bandwidth  # only relevant for bandpass/bandstop
        self._transition_width = transition_width
        self._type = type
        self._rebuild()
    
    def _rebuild(self):
        if self._type == 'lpf':
            bands = [0, self._freq, self._freq + self._transition_width, self.sample_rate/2]
            weights = [1, 0]
        elif self._type == 'hpf':
            bands = [0, self._freq - self._transition_width, self._freq, self.sample_rate/2]
            weights = [0, 1]
        elif self._type == 'bpf':
            band = (self.freq - self._bandwidth/2, self.freq + self._bandwidth/2)
            bands = [0, band[0] - self._transition_width, band[0], band[1], band[1] + self._transition_width, self.sample_rate/2]
            weights = [0, 1, 0]
        elif self._type == 'bsf':
            band = (self.freq - self._bandwidth/2, self.freq + self._bandwidth/2)
            bands = [0, band[0] - self._transition_width, band[0], band[1], band[1] + self._transition_width, self.sample_rate/2]
            weights = [1, 0, 1]
        taps = signal.remez(self._order + 1, bands, weights, Hz=self.sample_rate)
        # TODO: Maybe preserve input history post-rebuild?
        self.convolver = ShortConvolver(self.sample_rate, taps)
    
    def visualize_filter(self):
        w, h = signal.freqz(self.convolver.impulse_response, worN=2048)
        utility.plot_response(self.sample_rate, w, h, "FIR Frequency Response")

    @property
    def order(self):
        return self._order
    
    @property
    def freq(self):
        return self._freq

    @property
    def bandwidth(self):
        return self._bandwidth
    
    @property
    def transition_width(self):
        return self._transition_width
    
    @property
    def type(self):
        return self._type
    
    @order.setter
    def order(self, value):
        self._order = value
        self._rebuild()
    
    @freq.setter
    def freq(self, value):
        self._freq = value
        self._rebuild()
    
    @bandwidth.setter
    def bandwidth(self, value):
        self._bandwidth = value
        self._rebuild()
    
    @transition_width.setter
    def transition_width(self, value):
        self._transition_width = value
        self._rebuild()
    
    @type.setter
    def type(self, value):
        self._type = value
        self._rebuild()
    
    def process(self, input_buffer, output_buffer):
        self.convolver.process(input_buffer, output_buffer)