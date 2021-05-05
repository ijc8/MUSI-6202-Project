import math
import random

import numpy as np
from scipy.io import wavfile

from module import Module


# TODO: reduce duplication
INTERNAL_SAMPLERATE = 48000


class Granular(Module):
    def __init__(self, sample_rate, speed=1, filename="example.wav", grain_size=0.1):
        super().__init__(sample_rate)
        self.time = 0
        self.speed = speed
        self._grain_size = 100
        self.filename = filename
        self.grain_size = grain_size
        self.overlap = False
    
    @property
    def grain_size(self):
        return self._grain_size
    
    @grain_size.setter
    def grain_size(self, value):
        self._grain_size = value
        self.grain()

    @property
    def filename(self):
        return self._filename
    
    @filename.setter
    def filename(self, value):
        self._filename = value
        fs, data = wavfile.read(value)
        self.data = data[:, 0].astype(np.float) / np.iinfo(data.dtype).max
        self.wav_factor = fs / INTERNAL_SAMPLERATE
        self.grain()

    @property
    def overlap(self):
        return self._overlap

    @overlap.setter
    def overlap(self, value):
        self._overlap = value
        self.grain()
        self.current_grain = random.choice(self.grains)

    def grain(self, overlap=False):
        self.grains = []
        jump = 0
        while jump < len(self.data):
            winSize = min(int(np.random.rand() * int(self._grain_size * self.sample_rate - 2)) + 2, len(self.data) - jump)
            self.grains.append(self.data[jump:jump + winSize] * np.hanning(winSize))
            if overlap:
                hopSize = int(np.random.rand() * winSize)
            else:
                hopSize = winSize
            jump += hopSize

    def process(self, input_buffer, output_buffer):
        speed = self.speed * self.wav_factor
        time = self.time
        for i in range(len(output_buffer)):
            if time < 0:
                self.current_grain = random.choice(self.grains)
                time = len(self.current_grain) - 1.00001
            elif time >= len(self.current_grain) - 1:
                time = 0
                self.current_grain = random.choice(self.grains)
            index = math.floor(time)
            frac = time - index
            sample = (1-frac)*self.current_grain[index] + frac*self.current_grain[index+1]
            output_buffer[i] = sample
            time += speed
        self.time = time