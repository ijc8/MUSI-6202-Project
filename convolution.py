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
        output_buffer[:] = np.convolve(buffer_with_history, self.impulse_response, mode='valid')
        self.history[:] = input_buffer[-len(self.history):]
 

class ConvolutionFilter(Module):
    "Filter audio by convolving with Parks-McClellan/Remez exchange algorithm-designed FIR."

    def __init__(self, sample_rate, numtaps, cutoff, trans_width):
        super().__init__(sample_rate)
        taps = signal.remez(numtaps, [0, cutoff - trans_width, cutoff, sample_rate/2], [1, 0], Hz=sample_rate)
        w, h = signal.freqz(taps, [1], worN=2000)
        utility.plot_response(sample_rate, w, h, "Low-pass Filter")
        self.convolver = ShortConvolver(sample_rate, taps)
    
    def process(self, input_buffer, output_buffer):
        self.convolver.process(input_buffer, output_buffer)

# class delay(Module):
#     def __init__(self, sample_rate, delayTime=100, delayAmp=0.5):
#         super().__init__(sample_rate)
#         self.delayTime = delayTime
#         self.delayAmp = delayAmp

#     def process(self, input_buffer, output_buffer):
#         delayLenSamp = round(self.delayTime * self.sample_rate)
#         impulseResp = np.zeros(delayLenSamp)
#         impulseResp[0] = 1
#         impulseResp[-1] = self.delayAmp
#         #how to report the sound
#         freqs = np.covolve(input_buffer, impulseResp)
#         self.process(freqs, input_buffer, output_buffer)
#         self.time += len(input_buffer) / self.sample_rate

# class combfilter(Module):
#     def __init__(self, sample_rate, gain, delayT, delayTime, delayAmp):
#         # def __init__(self, sample_rate, freqm, ft, amp, ramp_amp, resonance):
#         super().__init__(sample_rate)
#         self.gain = gain
#         self.delayT = delayT
#         self.delay = delay( sample_rate, delayTime, delayAmp)
#         self.time = 0
#     def process(self, input_buffer, output_buffer):
#         for i in range(10):
#             #freqs+=delay(freqs,time)*gain

#         self.process(freqs, input_buffer, output_buffer)
#         self.time += len(input_buffer) / self.sample_rate

# class convReverb(Module):
#     def __init__(self, sample_rate, amp, gain, delayT, delayTime, delayAmp):
#     # def __init__(self, sample_rate, freqm, ft, amp, ramp_amp, resonance):
#         super().__init__(sample_rate)
#         self.combfilter = combfilter(sample_rate, gain, delayT, delayTime, delayAmp)
#         self.gain = gain
#         self.amp = amp
#     def process(self, input_buffer, output_buffer):
#         c1 = combfilter(input_buffer,31.12,0.827)/4
#         c2 = combfilter(input_buffer, 36.04, 0.805)/4
#         c3 = combfilter(input_buffer, 40.44, 0.783)/4
#         c4 = combfilter(input_buffer, 44.92, 0.764)/4
#         cTotal=c1+c2+c3+c4
#         freqs=input_buffer+cTotal*self.amp
#         self.process(freqs, input_buffer, output_buffer)
#         self.time += len(input_buffer) / self.sample_rate
