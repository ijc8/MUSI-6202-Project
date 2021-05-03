import numpy as np

from module import Module


class LinearResampler(Module):
    def __init__(self, sample_rate, target_rate):
        super().__init__(sample_rate)
        self.target_rate = target_rate
        self.source_time = 0
        self.last_sample = 0
    
    def process(self, input_buffer, output_buffer):
        source_time = self.source_time
        source_delta = self.sample_rate/self.target_rate
        # print('before', len(input_buffer), source_time)
        for i in range(len(output_buffer)):
            si = int(source_time)
            if source_time < 0:
                assert(source_time >= -1)
                y0 = self.last_sample
                y1 = input_buffer[si + 1]
            else:
                y0 = input_buffer[si]
                y1 = input_buffer[si + 1]
            output_buffer[i] = y0 + (y1 - y0) * (source_time - si)
            source_time += source_delta
        # print('after', source_time, source_time - len(input_buffer))
        source_time -= len(input_buffer)
        self.source_time = source_time
        self.last_samples = input_buffer[-1]

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

class CubicResampler(Module):
    def __init__(self, sample_rate, target_rate):
        super().__init__(sample_rate)
        self.target_rate = target_rate
        self.source_time = -1
        self.last_samples = np.zeros(4)

    def process(self, input_buffer, output_buffer):
        _spline = spline
        source_time = self.source_time
        source_delta = self.sample_rate/self.target_rate
        # print('before', len(input_buffer), source_time)
        for i in range(len(output_buffer)):
            si = int(source_time)
            if source_time < -2:
                assert(source_time >= -3)
                y0 = self.last_samples[-4]
                y1 = self.last_samples[-3]
                y2 = self.last_samples[-2]
                y3 = self.last_samples[-1]
            elif source_time < -1:
                y0 = self.last_samples[-3]
                y1 = self.last_samples[-2]
                y2 = self.last_samples[-1]
                y3 = input_buffer[si + 2]
            elif source_time < 0:
                y0 = self.last_samples[-2]
                y1 = self.last_samples[-1]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            elif source_time < 1:
                y0 = self.last_samples[-1]
                y1 = input_buffer[si]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            else:
                y0 = input_buffer[si - 1]
                y1 = input_buffer[si]
                y2 = input_buffer[si + 1]
                y3 = input_buffer[si + 2]
            output_buffer[i] = _spline(y0, y1, y2, y3, source_time - si)
            source_time += source_delta
        # print('after', source_time, source_time - len(input_buffer))
        source_time -= len(input_buffer)
        self.source_time = source_time
        self.last_samples = input_buffer[-4:]
