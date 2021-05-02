import ast
import readline

import sounddevice as sd

from delay import Delay
from example_module import ExampleModule
from quantize import Quantizer
from subtractive import SubtractiveSynth
from wah import AutoWah

chain = None

def callback(outdata, frames, time, status):
    outdata[:, 0] = 0
    for module in chain or []:
        module.process(outdata, outdata)

with sd.OutputStream(channels=1, callback=callback, blocksize=16384) as stream:
    modules = {
        "subtractive": SubtractiveSynth(stream.samplerate),
        "autowah": AutoWah(stream.samplerate, (100, 2000), 0, 0.5),
        "delay": Delay(stream.samplerate),
        "quantizer": Quantizer(stream.samplerate),
    }
    # {"sine": ExampleModule(stream.samplerate)}
    chain = [modules[name] for name in ["subtractive", "autowah", "delay", "quantizer"]]
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

