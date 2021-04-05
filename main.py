import ast
import readline

import sounddevice as sd

from example_module import ExampleModule
from subtractive import SubtractiveSynth

chain = None

def callback(outdata, frames, time, status):
    outdata[:, 0] = 0
    for module in chain or []:
        module.process(outdata, outdata)

with sd.OutputStream(channels=1, callback=callback, blocksize=1024) as stream:
    modules = {"subtractive": SubtractiveSynth(stream.samplerate)} # {"sine": ExampleModule(stream.samplerate)}
    chain = [modules[name] for name in ["subtractive"]]
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
                param_spec, value = params[0].split(" ", 1)
                module, param = param_spec.split(".")
                setattr(modules[module], param, ast.literal_eval(value))
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

