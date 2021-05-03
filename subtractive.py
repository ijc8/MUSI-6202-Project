import numpy as np

from module import Module
from filter import StateVariableFilter


class AdditiveSynth(Module):
    def __init__(self, sample_rate, coefficients):
        "Coefficients is a list of (freq, amplitude) pairs."
        super().__init__(sample_rate)
        self.phase = 0
        self.coefficients = coefficients
        self.freqs = np.array([c[0] for c in coefficients])[:,None]
        self.amps = np.array([c[1] for c in coefficients])[:,None]
    
    def process(self, input_buffer, output_buffer):
        # for freq, amplitude in self.coefficients:
            # output_buffer[:,0] += amplitude * np.sin(2*np.pi*freq*np.arange(len(output_buffer))/self.sample_rate + self.phase*freq)
        output_buffer[:] = np.sum(self.amps * np.sin(2*np.pi*self.freqs*np.arange(len(output_buffer))/self.sample_rate + self.phase*self.freqs), axis=0)
        self.phase += 2*np.pi*len(output_buffer)/self.sample_rate
        self.phase %= 2*np.pi


class NoiseSource(Module):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
    
    def process(self, input_buffer, output_buffer):
        output_buffer[:] = np.random.uniform(-1, 1, output_buffer.shape)


class SubtractiveSynth(Module):
    "Various sources with many harmonics (sawtooth, square, noise) + a resonant low-pass filter."

    def __init__(self, sample_rate, freq=55, source="sawtooth"):
        super().__init__(sample_rate)
        self.freq = freq
        self.source = source  # options: "sawtooth", "square", "noise"
        self.lpf = StateVariableFilter(sample_rate, freq*10, 1.0)
    
    # Wrap properties of internal LPF.
    # TODO: Could have less boilerplate here, and ensure these are exposed as parameters in `help`.
    # Maybe the Module interface should include get_parameters()?
    @property
    def cutoff(self):
        return self.lpf.freq
    
    @cutoff.setter
    def cutoff(self, value):
        self.lpf.freq = value

    @property
    def resonance(self):
        return self.lpf.resonance
    
    @resonance.setter
    def resonance(self, value):
        self.lpf.resonance = value

    @property
    def mode(self):
        return self.lpf.mode
    
    @resonance.setter
    def mode(self, value):
        self.lpf.mode = value
    
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == 'freq':
            self.sources = {
                "sawtooth": AdditiveSynth(self.sample_rate, [(k*self.freq, 2/np.pi*(-1)**k/k) for k in range(1, int(self.sample_rate/2/self.freq)+1)]),
                "square": AdditiveSynth(self.sample_rate, [(k*self.freq, 4/np.pi/k) for k in range(1, int(self.sample_rate/2/self.freq)+1, 2)]),
                "noise": NoiseSource(self.sample_rate),
            }

    def process(self, input_buffer, output_buffer):
        self.sources[self.source].process(input_buffer, output_buffer)
        self.lpf.process(output_buffer, output_buffer)
