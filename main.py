import ast
import readline

import sounddevice as sd

from example_module import ExampleModule

def callback(outdata, frames, time, status):
    for module in chain:
        module.process(outdata, outdata)

with sd.OutputStream(channels=1, callback=callback) as stream:
    modules = {"sine": ExampleModule(stream.samplerate)}
    chain = [modules[name] for name in ["sine"]]
    try:
        while stream.active:
            command, *params = input("> ").split(' ')
            if command == "get":
                module, param = params[0].split(".")
                print(getattr(modules[module], param))
            elif command == "set":
                module, param = params[0].split(".")
                setattr(modules[module], param, ast.literal_eval(params[1]))
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
        pass

