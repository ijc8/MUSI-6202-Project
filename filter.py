import numpy as np

from module import Module


class StateVariableFilter(Module):
    def __init__(self, sample_rate, freq, resonance, mode='lpf'):
        super().__init__(sample_rate)
        assert (resonance >= 0.5)
        self.resonance = resonance
        self.freq = freq
        self.prev_band, self.prev_low = 0, 0
        self.mode = mode
    
    @property
    def freq(self):
        return self._freq

    @freq.setter
    def freq(self, value):
        self._freq = value
        self.f1 = 2*np.sin(np.pi * value / self.sample_rate)

    @property
    def resonance(self):
        return self._resonance
    
    @resonance.setter
    def resonance(self, value):
        self._resonance = value
        self.q1 = 1/value

    def process(self, input_buffer, output_buffer):
        mode, q1, f1, prev_band, prev_low = self.mode, self.q1, self.f1, self.prev_band, self.prev_low
        for i in range(len(input_buffer)):
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


# Algorithm from http://www.musicdsp.org/showone.php?id=24
# Unfortunately, this seems too slow for real-time as-is.
class MoogLPF(Module):
    def __init__(self, sample_rate, cutoff=400, resonance=0.1):
        super().__init__(sample_rate)
        self.stage = np.zeros(4)
        self.delay = np.zeros(4)
        self._resonance = 0
        self.cutoff = cutoff
        self.resonance = resonance
    
    def process(self, input_buffer, output_buffer):
        resonance, stage, delay, p, k, t1, t2 = self._resonance, self.stage, self.delay, self.p, self.k, self.t1, self.t2
        for i, sample in enumerate(input_buffer):
            x = sample - resonance * stage[3]

            # Four cascaded one-pole filters (bilinear transform)
            stage[0] = x*p - k*stage[0]
            stage[1] = stage[0]*p - k*stage[1]
            stage[2] = stage[1]*p - k*stage[2]
            stage[3] = stage[2]*p - k*stage[3]
            stage += delay*p
        
            # Clipping band-limited sigmoid
            stage[3] -= (stage[3]*stage[3]*stage[3]) / 6
            
            delay[0] = x
            delay[1:] = stage[:-1]

            output_buffer[i] = stage[3]

    def __setattr__(self, name, value):
        if name == 'resonance':
            self._resonance = value
            self._update()
        elif name == 'cutoff':
            self._cutoff = value
            self._update()
        else:
            super().__setattr__(name, value)
    
    def _update(self):
        cutoff = 2 * self._cutoff / self.sample_rate
        self.p = cutoff * (1.8 - 0.8 * cutoff)
        self.k = 2 * np.sin(cutoff * np.pi * 0.5) - 1
        self.t1 = (1 - self.p) * 1.386249
        self.t2 = 12 + self.t1**2
        self.r = self._resonance * (self.t2 + 6.0 * self.t1) / (self.t2 - 6.0 * self.t1)
