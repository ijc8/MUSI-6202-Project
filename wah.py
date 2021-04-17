import numpy as np

from module import Module


# TODO: Reduce duplication with StateVariableFilter?
class ModulatedSVF(Module):
    def __init__(self, sample_rate, resonance, mode='lpf'):
        super().__init__(sample_rate)
        assert (resonance >= 0.5)
        self.resonance = resonance
        self.prev_band, self.prev_low = 0, 0
        self.mode = mode
    
    @property
    def resonance(self):
        return self._resonance
    
    @resonance.setter
    def resonance(self, value):
        self._resonance = value
        self.q1 = 1/value

    def process(self, freqs, input_buffer, output_buffer):
        f1s = 2*np.sin(np.pi * freqs / self.sample_rate)
        mode, q1, prev_band, prev_low = self.mode, self.q1, self.prev_band, self.prev_low
        for i in range(len(input_buffer)):
            f1 = f1s[i]
            low = prev_low + f1 * prev_band
            high = input_buffer[i] - low - q1*prev_band
            band = f1 * high + prev_band

            # TODO: If necessary, optimize by lifting the branch.
            if mode == 'lpf':
                output_buffer[i] = low
            elif mode == 'bpf':
                output_buffer[i] = band
            elif mode == 'hpf':
                output_buffer[i] = high
            elif mode == 'notch':
                output_buffer[i] = low + high

            prev_band = band
            prev_low = low
        self.prev_band = prev_band
        self.prev_low = prev_low


class AutoWah(Module):
    def __init__(self, sample_rate, freq_range, rate, resonance):
        super().__init__(sample_rate)
        self.freq_range = freq_range
        self.rate = rate
        self.bpf = ModulatedSVF(sample_rate, resonance, 'bpf')
        self.time = 0

    @property
    def resonance(self):
        return self.bpf.resonance
    
    @resonance.setter
    def resonance(self, value):
        self.bpf.resonance = value
    
    def process(self, input_buffer, output_buffer):
        times = self.time + np.arange(len(input_buffer))/self.sample_rate
        sweep_amp = (self.freq_range[1] - self.freq_range[0])/2
        sweep_center = (self.freq_range[0] + self.freq_range[1])/2
        # LFO:
        freqs = np.sin(2*np.pi*times*self.rate)*sweep_amp + sweep_center
        self.bpf.process(freqs, input_buffer, output_buffer)
        self.time += len(input_buffer)/self.sample_rate