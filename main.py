import ast
import readline

import numpy as np
import sounddevice as sd

from delay import Delay
from example_module import ExampleModule
from quantize import Quantizer
from resample import CubicResampler as Resampler
from subtractive import SubtractiveSynth
from wah import AutoWah


INTERNAL_SAMPLERATE = 48000
BLOCKSIZE = 4096

chain = None
resampler = None
buffer = None
quantizer = None

def callback(outdata, frames, time, status):
    if chain is None:
        return
    # Ensure we don't have unbounded history build-up (or dropped samples) in our resampler:
    # For linear resampler: buf = buffer if resampler.source_time >= -0.2 else buffer[:-1]
    buf = buffer if resampler.source_time >= -2 else buffer[:-1]
    # print(buf.shape)
    for module in chain:
        module.process(buf, buf)
    resampler.process(buf, outdata)
    quantizer.process(outdata, outdata)

with sd.OutputStream(channels=1, callback=callback, blocksize=BLOCKSIZE) as stream:
    print(f"Running with internal sample rate = {INTERNAL_SAMPLERATE}, output sample rate = {stream.samplerate}")
    resampler = Resampler(INTERNAL_SAMPLERATE, stream.samplerate)
    buffer = np.zeros(int(np.ceil(INTERNAL_SAMPLERATE / stream.samplerate * BLOCKSIZE)))
    quantizer = Quantizer(stream.samplerate)
    modules = {
        "subtractive": SubtractiveSynth(INTERNAL_SAMPLERATE),
        "autowah": AutoWah(INTERNAL_SAMPLERATE, (100, 2000), 0, 0.5),
        "delay": Delay(INTERNAL_SAMPLERATE),
        "resampler": resampler,
        "quantizer": quantizer,
    }
    # {"sine": ExampleModule(stream.samplerate)}
    # NOTE: Chain implicity ends with resampler, quantizer.
    chain = [modules[name] for name in ["subtractive", "autowah", "delay"]]
    try:
        while stream.active:
            try:
                command, *params = input("> ").split(" ", 1)
            except EOFError:
                # Allow Ctrl+D to exit.
                break
            if command == "get":
                module, *params = params[0].split(".")
                if module in modules:
                    value = modules[module]
                    for param in params:
                        value = getattr(value, param)
                    print(value)
                else:
                    print(f"No module named '{module}'.")
            elif command == "set":
                try:
                    param_spec, value = params[0].split(" ", 1)
                except ValueError:
                    print("Missing value.")
                    continue
                module, *params = param_spec.split(".")
                try:
                    value = ast.literal_eval(value)
                except ValueError:
                    # Just treat it as a string.
                    pass
                except SyntaxError as e:
                    print(e)
                    continue
                if module in modules:
                    container = modules[module]
                    for param in params[:-1]:
                        container = getattr(container, param)
                    setattr(container, params[-1], value)
                else:
                    print(f"No module named '{module}'.")
            elif command == "help":
                print("Available commands:")
                print("  get <module>.<param>")
                print("  set <module>.<param> <value>")
                print("  help")
                print("Modules and parameters:")
                # TODO: Recursively list parameters for embedded modules.
                for name, module in modules.items():
                    print("  " + name)
                    for attr in vars(module):
                        print(f"    {name}.{attr}")
    except KeyboardInterrupt:
        # Allow Ctrl+C to exit.
        pass

