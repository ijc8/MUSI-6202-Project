import ast
import os
import readline
import time
import wave

import mido
import numpy as np
import sounddevice as sd

from convolution import ConvolutionFilter
from delay import Delay
from envelope import Envelope
from filter import MoogLPF
from example_module import ExampleModule
from midi import MIDISource
from quantize import Quantizer
from resample import CubicResampler as Resampler
from subtractive import SubtractiveSynth
from tremolo import Tremolo
from wah import AutoWah


INTERNAL_SAMPLERATE = 48000
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

def midi_callback(pitch, velocity):
    modules["subtractive"].freq = 2**((pitch-69)/12)*440
    modules["envelope"].trigger(velocity)

def midi_help():
    print("MIDI commands:")
    print("  midi list")
    print("  midi connect [device name or index, defaults to 0]")
    print("  midi disconnect")
    print("  midi file <filename>")

def midi_command(params):
    global midi
    command, *params = params.split(" ", 1)
    if command == "list":
        print("Available MIDI inputs:")
        for index, name in enumerate(mido.get_input_names()):
            print(f"  {index}: {name}")
    elif command == "connect":
        if midi:
            print(f"Disconnected from '{midi.port.name}'.")
            midi.disconnect()
        name = None
        if params:
            try:
                index = int(params[0])
                name = mido.get_input_names()[index]
            except ValueError:
                name = params[0]
            except IndexError:
                print(f"No device with index {index}.")
        try:
            midi = MIDISource()
            midi.connect(midi_callback, name)
        except OSError:
            print(f"No device named '{name}'.")
            midi = None
            return
        print(f"Connected to '{midi.port.name}'.")
    elif command == "disconnect":
        if midi:
            print(f"Disconnected from '{midi.port.name}'.")
            midi.disconnect()
    elif command == "file":
        if not params:
            print("Usage: midi file <filename>")
            return
        try:
            mid = mido.MidiFile(params[0])
        except:
            print(f"Failed to open MIDI file '{params[0]}'.")
            return
        for message in mid.play():
            midi_callback(message.note, message.velocity)
    else:
        midi_help()

class SynthEngine:
    def __init__(self):
        global modules, resampler, quantizer, chain
        quantizer = Quantizer()
        modules = {
            "subtractive": SubtractiveSynth(INTERNAL_SAMPLERATE),
            "moog": MoogLPF(INTERNAL_SAMPLERATE),
            "convfilter": ConvolutionFilter(INTERNAL_SAMPLERATE),
            "envelope": Envelope(INTERNAL_SAMPLERATE),
            "autowah": AutoWah(INTERNAL_SAMPLERATE, (100, 2000), 0, 0.5),
            "delay": Delay(INTERNAL_SAMPLERATE),
            "tremolo": Tremolo(INTERNAL_SAMPLERATE),
            "quantizer": quantizer,
            "engine": self,
        }
        # NOTE: Chain implicity ends with resampler, quantizer.
        chain = [modules[name] for name in ["subtractive", "moog", "convfilter"]] # "envelope", "autowah", "tremolo", "delay"]]
        self.samplerate = 44100

    @property
    def samplerate(self):
        return self.external_samplerate
    
    @samplerate.setter
    def samplerate(self, value):
        restart = self.stop_stream()
        if restart:
            print("Stopping the stream to change the sample rate. (This will interrupt recording.)")
        self.external_samplerate = value
        self.setup()
        if restart:
            print("Restarting stream.")
            self.start_stream()

    def setup(self):
        global modules, chain, resampler, buffer, quantizer
        print(f"Setup: internal sample rate = {INTERNAL_SAMPLERATE}, external sample rate = {self.external_samplerate}, block size = {BLOCKSIZE}")
        resampler = Resampler(INTERNAL_SAMPLERATE, self.external_samplerate)
        buffer = resampler.make_source_buffer(BLOCKSIZE)
        modules["resampler"] = resampler

    def start_stream(self):
        global stream
        if stream:
            return False
        stream = sd.OutputStream(channels=1, callback=callback, blocksize=BLOCKSIZE, samplerate=self.external_samplerate)
        assert(stream.samplerate == self.external_samplerate)
        stream.start()
        return True

    def stop_stream(self):
        global stream, recording_out
        if not stream:
            return False
        stream.stop()
        stream = None
        if recording_out:
            recording_out.close()
            recording_out = None
        return True
    
    def get_param(self, params):
        module, *params = params.split(".")
        try:
            value = modules[module]
        except KeyError:
            print(f"No such module '{module}'.")
            raise
        for param in params:
            try:
                value = getattr(value, param)
            except AttributeError:
                print(f"No such parameter '{param}'.")
                raise
        return value

    def handle_command(self, command, params):
        if command == "start":
            if not self.start_stream():
                print("Already running!")
        elif command == "midi":
            midi_command(params)
        elif command == "stop":
            if not self.stop_stream():
                print("Not running!")
        elif command == "record":
            filename = params or "out.wav"
            if not filename.endswith(".wav"):
                filename += ".wav"
            if os.path.exists(filename):
                overwrite = input(f"File '{filename}' already exists. Overwrite? [y/N] ")
                if not overwrite.lower().startswith('y'):
                    print("Not overwriting.")
                    return
            print(f"Recording to '{filename}'. Type 'stop' to stop.")
            recording_out = wave.open(filename, 'wb')
            recording_out.setnchannels(1)
            recording_out.setsampwidth(2)
            recording_out.setframerate(self.external_samplerate)
            self.start_stream()
        elif command == "render":
            duration, *params = params.split(" ", 1)
            duration = float(duration)
            filename = params[0] if params else "out.wav"
            if not filename.endswith(".wav"):
                filename += ".wav"
            if os.path.exists(filename):
                overwrite = input(f"File '{filename}' already exists. Overwrite? [y/N] ")
                if not overwrite.lower().startswith('y'):
                    print("Not overwriting.")
                    return
            if self.stop_stream():
                print("Stopping the stream to render to file. (Restart with 'start'.)")
            with wave.open(filename, 'wb') as w:
                w.setnchannels(1)
                # NOTE: For simplicity, we always save a 16-bit wave file, even if the bit depth of the content (post-quantization) is lower.
                # (Wave files can only store bit depths in multiples of 8, anyway.)
                w.setsampwidth(2)
                w.setframerate(self.external_samplerate)
                # Convert duration to samples.
                duration = int(duration * self.external_samplerate)
                outdata = np.zeros(BLOCKSIZE)
                start_time = time.time()
                for block in range(duration // BLOCKSIZE):
                    callback(outdata)
                    w.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))
                    p = int(block * BLOCKSIZE / duration * 50)
                    progress = '=' * p + ' ' * (50 - p)
                    print(f"{block * BLOCKSIZE / duration * 100:6.2f}% [{progress}] {block * BLOCKSIZE / self.external_samplerate:6.2f}/{duration / self.external_samplerate:.2f}", end='\r')
                # Last block:
                remainder = duration - (block * BLOCKSIZE)
                if remainder:
                    outdata = outdata[:remainder]
                    callback(outdata)
                    w.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))
                real_time = time.time() - start_time
                rendered_time = duration / self.external_samplerate
                print(f"{100:6.2f}% [{'=' * 50}] {rendered_time:6.2f}/{rendered_time:.2f}")
                print(f"Rendered {rendered_time:.2f}s to '{filename}' in {real_time:.2f}s ({rendered_time/real_time:.2f}x).")
        elif command == "get":
            try:
                print(self.get_param(params))
            except (KeyError, AttributeError):
                return
        elif command == "set":
            param_spec, value = params.split(" ", 1)
            if value == "":
                # TODO: Maybe allow defaults?
                print("Missing value.")
                return
            module, *params = param_spec.split(".")
            try:
                value = ast.literal_eval(value)
            except ValueError:
                # Just treat it as a string.
                pass
            except SyntaxError as e:
                print(e)
                return
            if module in modules:
                container = modules[module]
                for param in params[:-1]:
                    container = getattr(container, param)
                setattr(container, params[-1], value)
            else:
                print(f"No module named '{module}'.")
        elif command == "plot":
            try:
                filter = self.get_param(params)
            except (KeyError, AttributeError):
                return
            filter.visualize_filter()
        elif command in ["exit", "quit"]:
            print("Farewell.")
            self.running = False
            return
        elif command == "help":
            help(full=True)
        elif command == "":
            pass
        else:
            print(f"Unrecognized command '{command}'.")
            help(full=False)

    def run(self):
        self.running = True
        try:
            while self.running:
                try:
                    command, *params = input("> ").split(" ", 1)
                except EOFError:
                    # Allow Ctrl+D to exit.
                    print()
                    self.running = False
                    return
                self.handle_command(command, params[0] if params else '')
        except KeyboardInterrupt:
            # Allow Ctrl+C to exit.
            print()

        self.stop_stream()

engine = SynthEngine()
engine.run()