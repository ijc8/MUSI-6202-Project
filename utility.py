import matplotlib.pyplot as plt
import numpy as np

# SOURCE: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.remez.html
def plot_response(fs, w, h, title):
    "Utility function to plot response functions"

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(0.5*fs*w/np.pi, 20*np.log10(np.abs(h)))
    ax.set_ylim(-40, 5)
    ax.set_xlim(0, 0.5*fs)
    ax.grid(True)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('Gain (dB)')
    ax.set_title(title)
    plt.show(block=False)