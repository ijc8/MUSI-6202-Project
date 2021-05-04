import numpy as np

from module import Module


class ModulatedDelay(Module):
    def __init__(self, sample_rate, duration, mix, feedback):
        super().__init__(sample_rate)
        self.buffer = np.zeros(int(duration * sample_rate))
        self.mix = mix
        self.feedback = feedback
        self.buffer_index = 0
    
    @property
    def duration(self):
        return len(self.buffer)/self.sample_rate
    
    @duration.setter
    def duration(self, value):
        # NOTE: Changing the max delay clears the buffer.
        self.buffer = np.zeros(int(duration * sample_rate))
    
    def process(self, delays, input_buffer, output_buffer):
        buffer, buffer_index, mix, feedback = self.buffer, self.buffer_index, self.mix, self.feedback
        for i in range(len(input_buffer)):
            delay = delays[i]
            d = int(delay)
            frac = delay - d
            out = frac * buffer[(buffer_index - d - 1) % len(buffer)] + (1 - frac) * buffer[(buffer_index - d) % len(buffer)]
            buffer[buffer_index] = (1 - feedback) * input_buffer[i] + feedback * out
            output_buffer[i] = mix * out + (1-mix) * input_buffer[i]
            buffer_index += 1
            if buffer_index >= len(buffer):
                buffer_index %= len(buffer)
        self.buffer_index = buffer_index


class Delay(Module):
    def __init__(self, sample_rate):
        super().__init__(sample_rate)
        self.delay = ModulatedDelay(sample_rate, 1.0, 1.0, 0)
        self.time = 0
        self._fixed_delay = 0
        self._mod_amp = 0
        self.preset = "chorus"
    
    @property
    def mod_amp(self):
        return self._mod_amp
    
    @mod_amp.setter
    def mod_amp(self, value):
        if self.delay.duration < (self._fixed_delay + abs(self._mod_amp)):
            self.delay.duration = self._fixed_delay + abs(self._mod_amp)
        self._mod_amp = value
    
    @property
    def fixed_delay(self):
        return self._fixed_delay

    @fixed_delay.setter
    def fixed_delay(self, value):
        if self.delay.duration < (self._fixed_delay + abs(self._mod_amp)):
            self.delay.duration = self._fixed_delay + abs(self._mod_amp)
        self._fixed_delay = value
    
    @property
    def preset(self):
        return self._preset

    @preset.setter
    def preset(self, value):
        # Presets inspired by examples from class.
        if value == "vibrato":
            # Comments connect these to the slides:
            self.fixed_delay = .005  # M
            self.mod_amp = .005      # A, but in seconds instead of samples
            self.rate = 1            # f_mod
            self.delay.mix = 1       # FF/(BL+FF)
            self.delay.feedback = 0
        elif value == "flanger":
            self.fixed_delay = .002
            self.mod_amp = .002
            self.rate = 0.2
            self.delay.mix = 0.5
            self.delay.feedback = 0
        elif value == "flanger_feedback":
            self.fixed_delay = .002
            self.mod_amp = .002
            self.rate = 0.2
            self.delay.mix = 0.5
            self.delay.feedback = 0.7
        elif value == "chorus":
            self.fixed_delay = .002
            self.mod_amp = .002
            self.rate = 1.5
            self.delay.mix = 0.4
            self.delay.feedback = 0
        elif value == "chorus_feedback":
            self.fixed_delay = .002
            self.mod_amp = .002
            self.rate = 1.5
            self.delay.mix = 0.4
            self.delay.feedback = 0.7
        elif value == "slapback":
            self.fixed_delay = 0.02
            self.mod_amp = 0
            self.rate = 0
            self.delay.mix = 0.5
            self.delay.feedback = 0
        elif value == "echo":
            self.fixed_delay = 0.05
            self.mod_amp = 0
            self.rate = 0
            self.delay.mix = 0.5
            self.delay.feedback = 0
        else:
            raise NotImplementedError(f"Unknown preset '{value}'")
        self._preset = value
    
    def process(self, input_buffer, output_buffer):
        times = self.time + np.arange(len(input_buffer))/self.sample_rate
        delays = (np.sin(2*np.pi*times*self.rate)*self._mod_amp + self._fixed_delay)*self.sample_rate
        self.time += len(input_buffer)/self.sample_rate
        return self.delay.process(delays, input_buffer, output_buffer)