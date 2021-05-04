import ast
import os
import readline
import time
import wave

import mido
import numpy as np
import sounddevice as sd

from delay import Delay
from envelope import Envelope
from example_module import ExampleModule
from midi import MIDISource
from quantize import Quantizer
from resample import CubicResampler as Resampler
from subtractive import SubtractiveSynth
from tremolo import Tremolo
from wah import AutoWah


INTERNAL_SAMPLERATE = 48000
EXTERNAL_SAMPLERATE = 44100
BLOCKSIZE = 512

modules = None
chain = None
resampler = None
buffer = None
quantizer = None
stream = None
recording_out = None
midi = None

def callback(outdata, *ignored):
    buf = buffer[:resampler.get_source_blocksize(BLOCKSIZE)]
    for module in chain:
        module.process(buf, buf)
    resampler.process(buf, outdata)
    quantizer.process(outdata, outdata)
    if recording_out:
        recording_out.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))

def setup():
    global modules, chain, resampler, buffer, quantizer
    print(f"Setup: internal sample rate = {INTERNAL_SAMPLERATE}, external sample rate = {EXTERNAL_SAMPLERATE}")
    resampler = Resampler(INTERNAL_SAMPLERATE, EXTERNAL_SAMPLERATE)
    buffer = resampler.make_source_buffer(BLOCKSIZE)
    quantizer = Quantizer(EXTERNAL_SAMPLERATE)
    modules = {
        "subtractive": SubtractiveSynth(INTERNAL_SAMPLERATE),
        "envelope": Envelope(INTERNAL_SAMPLERATE),
        "autowah": AutoWah(INTERNAL_SAMPLERATE, (100, 2000), 0, 0.5),
        "delay": Delay(INTERNAL_SAMPLERATE),
        "tremolo": Tremolo(INTERNAL_SAMPLERATE),
        "resampler": resampler,
        "quantizer": quantizer,
    }
    # NOTE: Chain implicity ends with resampler, quantizer.
    chain = [modules[name] for name in ["subtractive", "envelope", "autowah", "tremolo", "delay"]]

def stop():
    global stream, recording_out
    if stream:
        stream.stop()
        stream = None
        if recording_out:
            recording_out.close()
            recording_out = None
        return True
    return False

def help(full=False):
    print("Available commands:")
    print("  start")
    print("  stop")
    print("  record [filename, defaults to 'out.wav']")
    print("  render <duration in seconds> [filename, defaults to 'out.wav']")
    print("  get <module>.<param>")
    print("  set <module>.<param> <value>")
    print("  help")
    midi_help()
    if full:
        print("Modules and parameters:")
        # TODO: Recursively list parameters for embedded modules.
        for name, module in modules.items():
            print("  " + name)
            for attr in vars(module):
                print(f"    {name}.{attr}")

setup()

def midi_callback(pitch, velocity):
    modules["subtractive"].freq = 2**((pitch-69)/12)*440
    modules["envelope"].trigger(velocity)

def midi_help():
    print("MIDI commands:")
    print("  midi list")
    print("  midi connect [device name]")
    print("  midi disconnect")

def midi_command(params):
    global midi
    command, *params = params.split(" ", 1)
    if command == "list":
        print("Available MIDI inputs:")
        for name in mido.get_input_names():
            print("  " + name)
    elif command == "connect":
        if midi:
            print(f"Disconnected from '{midi.port.name}'.")
            midi.disconnect()
        midi = MIDISource()
        midi.connect(midi_callback, params[0] if params else None)
        print(f"Connected to '{midi.port.name}'.")
    elif command == "disconnect":
        if midi:
            print(f"Disconnected from '{midi.port.name}'.")
            midi.disconnect()
    else:
        midi_help()

try:
    while True:
        try:
            command, *params = input("> ").split(" ", 1)
        except EOFError:
            # Allow Ctrl+D to exit.
            print()
            break
        if command == "start":
            if stream:
                print("Already running!")
            else:
                stream = sd.OutputStream(channels=1, callback=callback, blocksize=BLOCKSIZE, samplerate=EXTERNAL_SAMPLERATE)
                assert(stream.samplerate == EXTERNAL_SAMPLERATE)
                stream.start()
        elif command == "midi":
            midi_command(params[0] if params else '')
        elif command == "stop":
            if not stop():
                print("Not running!")
        elif command == "record":
            filename = params[0] if params else "out.wav"
            if not filename.endswith(".wav"):
                filename += ".wav"
            if os.path.exists(filename):
                overwrite = input(f"File '{filename}' already exists. Overwrite? [y/N] ")
                if not overwrite.lower().startswith('y'):
                    print("Not overwriting.")
                    continue
            print(f"Recording to '{filename}'. Type 'stop' to stop.")
            recording_out = wave.open(filename, 'wb')
            recording_out.setnchannels(1)
            recording_out.setsampwidth(2)
            recording_out.setframerate(EXTERNAL_SAMPLERATE)
            if not stream:
                stream = sd.OutputStream(channels=1, callback=callback, blocksize=BLOCKSIZE, samplerate=EXTERNAL_SAMPLERATE)
                assert(stream.samplerate == EXTERNAL_SAMPLERATE)
                stream.start()
        elif command == "render":
            duration, *params = params[0].split(" ", 1)
            duration = float(duration)
            filename = params[0] if params else "out.wav"
            if not filename.endswith(".wav"):
                filename += ".wav"
            if os.path.exists(filename):
                overwrite = input(f"File '{filename}' already exists. Overwrite? [y/N] ")
                if not overwrite.lower().startswith('y'):
                    print("Not overwriting.")
                    continue
            stop()
            with wave.open(filename, 'wb') as w:
                w.setnchannels(1)
                # NOTE: For simplicity, we always save a 16-bit wave file, even if the bit depth of the content (post-quantization) is lower.
                # (Wave files can only store bit depths in multiples of 8, anyway.)
                w.setsampwidth(2)
                w.setframerate(EXTERNAL_SAMPLERATE)
                # Convert duration to samples.
                duration = int(duration * EXTERNAL_SAMPLERATE)
                outdata = np.zeros(BLOCKSIZE)
                start_time = time.time()
                for block in range(duration // BLOCKSIZE):
                    callback(outdata)
                    w.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))
                    p = int(block * BLOCKSIZE / duration * 50)
                    progress = '=' * p + ' ' * (50 - p)
                    print(f"{block * BLOCKSIZE / duration * 100:6.2f}% [{progress}] {block * BLOCKSIZE / EXTERNAL_SAMPLERATE:6.2f}/{duration / EXTERNAL_SAMPLERATE:.2f}", end='\r')
                # Last block:
                remainder = duration - (block * BLOCKSIZE)
                if remainder:
                    outdata = outdata[:remainder]
                    callback(outdata)
                    w.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))
                real_time = time.time() - start_time
                rendered_time = duration / EXTERNAL_SAMPLERATE
                print(f"{100:6.2f}% [{'=' * 50}] {rendered_time:6.2f}/{rendered_time:.2f}")
                print(f"Rendered {rendered_time:.2f}s to '{filename}' in {real_time:.2f}s ({rendered_time/real_time:.2f}x).")
        elif command == "get":
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
            help(full=True)
        else:
            print(f"Unrecognized command '{command}'.")
            help(full=False)

except KeyboardInterrupt:
    # Allow Ctrl+C to exit.
    print()
    pass

stop()