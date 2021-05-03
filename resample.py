import math
import numpy as np

from module import Module


class Resampler(Module):
    "Abstract base class for resamplers."
    LOOKAHEAD = None
    HISTORY = None

    def __init__(self, sample_rate, target_rate):
        super().__init__(sample_rate)
        self.target_rate = target_rate
        self.source_time = -(self.HISTORY - 1)
        self.last_samples = np.zeros(self.HISTORY)

    def make_source_buffer(self, target_blocksize):
        return np.zeros(int(np.ceil(self.sample_rate / self.target_rate * target_blocksize)))

    def get_source_blocksize(self, target_blocksize):
        # Buffer size needed to avoid IndexError:
        highest_index = int((target_blocksize-1)*self.sample_rate/self.target_rate+self.source_time+self.LOOKAHEAD)
        # print("expecting highest index of", highest_index)
        # print("need at least", min_samples, "samples")
        # Buffer size needed to avoid storing more history/dropping samples:
        # print("need at most", self.source_time + self.sample_rate/self.target_rate*target_blocksize + (self.HISTORY - 1), "samples")
        min_samples = highest_index + 1
        return min_samples


class LinearResampler(Resampler):
    LOOKAHEAD = 1
    HISTORY = 2
    
    def process(self, input_buffer, output_buffer):
        source_time = self.source_time
        source_delta = self.sample_rate/self.target_rate
        # print('before', len(input_buffer), source_time)
        for i in range(len(output_buffer)):
            si = math.floor(source_time)
            if source_time >= 0:
                y0 = input_buffer[si]
                y1 = input_buffer[si + 1]
            elif source_time >= -1:
                y0 = self.last_samples[-1]
                y1 = input_buffer[si + 1]
            elif source_time >= -2:
                y0 = self.last_samples[-2]
                y1 = self.last_samples[-1]
            else:
                # Shouldn't happen; we only want to store two samples from history.
                assert(False)
            output_buffer[i] = y0 + (y1 - y0) * (source_time - si)
            source_time += source_delta
        # print('after', source_time, source_time - len(input_buffer))
        source_time -= len(input_buffer)
        self.source_time = source_time
        # NOTE: The copy here is essential, as the underlying input_buffer may be modified later.
        self.last_samples = input_buffer[-2:].copy()

def spline(y0, y1, y2, y3, x):
    a = y3 - y2 - y0 + y1
    b = y0 - y1 - a
    c = y2 - y0
    d = y1
    return a*x**3 + b*x**2 + c*x + d

# Another option (see http://yehar.com/blog/?p=197)
# def spline(y_1, y0, y1, y2, x):
#     ym1py1 = y_1+y1
#     c0 = 1/6.0*ym1py1 + 2/3.0*y0
#     c1 = 1/2.0*(y1-y_1)
#     c2 = 1/2.0*ym1py1 - y0
#     c3 = 1/2.0*(y0-y1) + 1/6.0*(y2-y_1)
#     return ((c3*x+c2)*x+c1)*x+c0

class CubicResampler(Resampler):
    LOOKAHEAD = 2
    HISTORY = 4

    def process(self, input_buffer, output_buffer):
        _spline = spline
        source_time = self.source_time
        source_delta = self.sample_rate/self.target_rate
        last_samples = self.last_samples
        # print('before', len(input_buffer), len(output_buffer), source_time)
        for i in range(len(output_buffer)):
            si = math.floor(source_time)
            if source_time >= 1:
                y0 = input_buffer[si - 1]
                y1 = input_buffer[si]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            elif source_time >= 0:
                y0 = last_samples[-1]
                y1 = input_buffer[si]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            elif source_time >= -1:
                y0 = last_samples[-2]
                y1 = last_samples[-1]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            elif source_time >= -2:
                y0 = last_samples[-3]
                y1 = last_samples[-2]
                y2 = last_samples[-1]
                y3 = input_buffer[si + 2]
            elif source_time >= -3:
                y0 = last_samples[-4]
                y1 = last_samples[-3]
                y2 = last_samples[-2]
                y3 = last_samples[-1]
            else:
                # Shouldn't happen; we only want to store four samples from history.
                assert(False)
            output_buffer[i] = _spline(y0, y1, y2, y3, source_time - si)
            source_time += source_delta
        # print("highest index was actually", si + 2)
        # print('after', source_time, source_time - len(input_buffer))
        source_time -= len(input_buffer)
        self.source_time = source_time
        # NOTE: The copy here is essential, as the underlying input_buffer may be modified later.
        self.last_samples = input_buffer[-4:].copy()
