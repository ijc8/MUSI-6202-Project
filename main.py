import ast
import readline

import sounddevice as sd

from example_module import ExampleModule
from subtractive import SubtractiveSynth
from wah import AutoWah

chain = None

def callback(outdata, frames, time, status):
    outdata[:, 0] = 0
    for module in chain or []:
        module.process(outdata, outdata)

with sd.OutputStream(channels=1, callback=callback, blocksize=2048) as stream:
    modules = {"subtractive": SubtractiveSynth(stream.samplerate), "autowah": AutoWah(stream.samplerate, (100, 2000), 1, 2)}
    # {"sine": ExampleModule(stream.samplerate)}
    chain = [modules[name] for name in ["subtractive", "autowah"]]
    try:
        while stream.active:
            try:
                command, *params = input("> ").split(" ", 1)
            except EOFError:
                # Allow Ctrl+D to exit.
                break
            if command == "get":
                module, param = params[0].split(".")
                print(getattr(modules[module], param))
            elif command == "set":
                try:
                    param_spec, value = params[0].split(" ", 1)
                except ValueError:
                    print("Missing value.")
                    continue
                module, param = param_spec.split(".")
                try:
                    value = ast.literal_eval(value)
                except ValueError:
                    # Just treat it as a string.
                    pass
                except SyntaxError as e:
                    print(e)
                    continue
                setattr(modules[module], param, value)
            elif command == "help":
                print("Available commands:")
                print("  get <module.param>")
                print("  set <module>.<param> <value>")
                print("  help")
                print("Modules and parameters:")
                for name, module in modules.items():
                    print("  " + name)
                    for attr in vars(module):
                        print(f"    {name}.{attr}")
    except KeyboardInterrupt:
        # Allow Ctrl+C to exit.
        pass

