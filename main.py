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
from granular import Granular
from example_module import ExampleModule
from midi import MIDISource
from module import Module
from quantize import Quantizer
from resample import CubicResampler as Resampler
from subtractive import SubtractiveSynth
from tremolo import Tremolo
from wah import AutoWah


INTERNAL_SAMPLERATE = 48000


# One-off module to combine our two synth sources.
class Mixer(Module):
    def __init__(self, a, b, mix=0.5):
        self.a = a
        self.b = b
        self.mix = mix
    
    def process(self, input_buffer, output_buffer):
        # NOTE: Overwrites input_buffer.
        self.a.process(input_buffer, input_buffer)
        self.b.process(input_buffer, output_buffer)
        input_buffer *= (1 - self.mix)
        output_buffer *= self.mix
        output_buffer += input_buffer


class SynthEngine:
    PARAMETERS = ("gain", "samplerate")

    def __init__(self):
        self.stream = None
        self.recording_out = None
        self.midi = None
        self.osc = None
        self.quantizer = Quantizer()
        self.envelope = Envelope(INTERNAL_SAMPLERATE)
        subtractive = SubtractiveSynth(INTERNAL_SAMPLERATE)
        granular = Granular(INTERNAL_SAMPLERATE)
        mixer = Mixer(subtractive, granular, 0.8)
        moog = MoogLPF(INTERNAL_SAMPLERATE)
        convfilter = ConvolutionFilter(INTERNAL_SAMPLERATE)
        autowah = AutoWah(INTERNAL_SAMPLERATE, (100, 2000), 0.5, 0.5)
        tremolo = Tremolo(INTERNAL_SAMPLERATE)
        delay = Delay(INTERNAL_SAMPLERATE)
        self.modules = {
            "subtractive": subtractive,
            "moog": moog,
            "convfilter": convfilter,
            "envelope": self.envelope,
            "autowah": autowah,
            "delay": delay,
            "tremolo": tremolo,
            "quantizer": self.quantizer,
            "engine": self,
            "granular": granular,
            "mixer": mixer,
        }
        # Disable envelope by default, until a MIDI source is specified.
        self.envelope.mix = 0
        # NOTE: Chain implicity ends with resampler, quantizer.
        self.chain = [mixer, moog, convfilter, self.envelope, autowah, tremolo, delay]
        self._blocksize = 2048
        self.samplerate = 44100
        self.gain = 1

    def process(self, outdata, *ignored):
        internal_blocksize = self.resampler.get_source_blocksize(len(outdata))
        buf = self.buffer[:internal_blocksize]
        scratch_buf = self.scratch_buffer[:internal_blocksize]
        buf[:] = 0
        for module in self.chain:
            module.process(buf, scratch_buf)
            scratch_buf *= module.mix
            buf *= (1 - module.mix)
            buf += scratch_buf
        buf *= self.gain
        self.resampler.process(buf, outdata)
        self.quantizer.process(outdata, outdata)
        if self.recording_out:
            self.recording_out.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))

    def handle_midi(self, pitch, velocity):
        self.modules["subtractive"].freq = 2**((pitch-69)/12)*440
        self.envelope.trigger(velocity)

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
    
    @property
    def blocksize(self):
        return self._blocksize
    
    @blocksize.setter
    def blocksize(self, value):
        restart = self.stop_stream()
        if restart:
            print("Stopping the stream to change the block size. (This will interrupt recording.)")
        self._blocksize = value
        self.setup()
        if restart:
            print("Restarting stream.")
            self.start_stream()

    def setup(self):
        print(f"Setup: internal sample rate = {INTERNAL_SAMPLERATE}, external sample rate = {self.external_samplerate}, block size = {self._blocksize}")
        self.resampler = Resampler(INTERNAL_SAMPLERATE, self.external_samplerate)
        self.buffer = self.resampler.make_source_buffer(self._blocksize)
        self.scratch_buffer = self.resampler.make_source_buffer(self._blocksize)
        self.modules["resampler"] = self.resampler

    def start_stream(self):
        if self.stream:
            return False
        try:
            self.stream = sd.OutputStream(channels=1, callback=self.process, blocksize=self._blocksize, samplerate=self.external_samplerate)
        except sd.PortAudioError:
            print(f"Failed with channels = 1, samplerate={self.external_samplerate}. Falling back to device defaults.")
            self.stream = sd.OutputStream(callback=self.process, blocksize=self._blocksize)
            print(f"Now using channels = {self.stream.channels}, samplerate={self.stream.samplerate}")
            self.external_samplerate = self.stream.samplerate
            self.setup()
        assert(self.stream.samplerate == self.external_samplerate)
        self.stream.start()
        return True

    def stop_stream(self):
        if not self.stream:
            return False
        self.stream.stop()
        self.stream = None
        if self.recording_out:
            self.recording_out.close()
            self.recording_out = None
        return True
    
    def get_param(self, params):
        module, *params = params.split(".")
        try:
            value = self.modules[module]
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

    def help(self, full=False):
        print("Available commands:")
        print("  start")
        print("  stop")
        print("  record [filename, defaults to 'out.wav']")
        print("  render <duration in seconds> [filename, defaults to 'out.wav']")
        print("  get <module>.<param>")
        print("  set <module>.<param> <value>")
        print("  plot <filter module>")
        print("  help")
        self.midi_help()
        self.osc_help()
        if full:
            print("Modules and parameters:")
            # TODO: Recursively list parameters for embedded modules.
            for name, module in self.modules.items():
                print("  " + name)
                for param in module.PARAMETERS:
                    value = getattr(module, param)
                    if isinstance(value, Module):
                        for subparam in value.PARAMETERS:
                            print(f"    {name}.{param}.{subparam}: {getattr(value, subparam)}")
                    else:
                        print(f"    {name}.{param}: {value}")

    def midi_help(self):
        print("MIDI commands:")
        print("  midi list")
        print("  midi connect [device name or index, defaults to 0]")
        print("  midi disconnect")
        print("  midi file <filename>")

    def handle_midi_command(self, command, params):
        if command == "list":
            print("Available MIDI inputs:")
            for index, name in enumerate(mido.get_input_names()):
                print(f"  {index}: {name}")
        elif command == "connect":
            if self.midi:
                print(f"Disconnected from '{self.midi.port.name}'.")
                self.midi.disconnect()
            name = None
            if params:
                try:
                    index = int(params)
                    name = mido.get_input_names()[index]
                except ValueError:
                    name = params
                except IndexError:
                    print(f"No device with index {index}.")
            try:
                self.midi = MIDISource()
                self.midi.connect(self.handle_midi, name)
            except OSError:
                print(f"No device named '{name}'.")
                self.midi = None
                return
            print(f"Connected to '{self.midi.port.name}'; enabling envelope.")
            self.envelope.mix = 1
        elif command == "disconnect":
            if self.midi:
                print(f"Disconnected from '{self.midi.port.name}'; disabling envelope.")
                self.midi.disconnect()
                self.midi = None
                self.envelope.mix = 0
        elif command == "file":
            if not params:
                print("Usage: midi file <filename>")
                return
            try:
                mid = mido.MidiFile(params)
            except:
                print(f"Failed to open MIDI file '{params}'.")
                return
            self.envelope.mix = 1
            for message in mid.play():
                self.handle_midi(message.note, message.velocity)
            if not self.midi:
                self.envelope.mix = 0
        else:
            self.midi_help()
    
    def osc_help(self):
        print("OSC commands:")
        print("  osc start [port, defaults to 8000]")
        print("  osc stop")
        print("  (Responses to `/<module>/<param> <value>`; e.g. `/subtractive/freq 400`)")
    
    def stop_osc(self):
        try:
            self.osc.stop()
            self.osc.default_socket = None
            return True
        except RuntimeError:
            return False
    
    def handle_osc_command(self, command, params):
        try:
            from oscpy.server import OSCThreadServer
        except ImportError:
            print("OSC commands require oscpy (run `pip install oscpy`).")
            return
    
        if command == "start":
            port = 8000
            if params:
                try:
                    port = int(params)
                except ValueError:
                    print("Usage: osc start [port, defaults to 8000]")
                    return
            if not self.osc:
                self.osc = OSCThreadServer(advanced_matching=True, default_handler=self.handle_osc_message)
            elif self.stop_osc():
                print("Stopped server.")
            self.osc.listen(address='0.0.0.0', port=port, default=True)
            print(f"Started server on port {port}.")
        elif command == "stop":
            if self.stop_osc():
                print("Stopped server.")
            else:
                print("Not running!")
        else:
            self.osc_help()

    def handle_osc_message(self, address, value):
        print("Received OSC message:", address, value)
        # Set a parameter via OSC.
        module, *params = address.decode('utf8').strip("/").split("/")
        if module in self.modules:
            container = self.modules[module]
            for param in params[:-1]:
                container = getattr(container, param)
            setattr(container, params[-1], value)
        else:
            print(f"No module named '{module}'.")

    def handle_command(self, command, params):
        if command == "midi":
            command, *params = params.split(" ", 1)
            self.handle_midi_command(command, params[0] if params else '')
        elif command == "osc":
            command, *params = params.split(" ", 1)
            self.handle_osc_command(command, params[0] if params else '')
        elif command == "start":
            if not self.start_stream():
                print("Already running!")
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
            self.recording_out = wave.open(filename, 'wb')
            self.recording_out.setnchannels(1)
            self.recording_out.setsampwidth(2)
            self.recording_out.setframerate(self.external_samplerate)
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
                    self.process(outdata)
                    w.writeframes((outdata * np.iinfo(np.int16).max).astype(np.int16))
                    p = int(block * BLOCKSIZE / duration * 50)
                    progress = '=' * p + ' ' * (50 - p)
                    print(f"{block * BLOCKSIZE / duration * 100:6.2f}% [{progress}] {block * BLOCKSIZE / self.external_samplerate:6.2f}/{duration / self.external_samplerate:.2f}", end='\r')
                # Last block:
                remainder = duration - (block * BLOCKSIZE)
                if remainder:
                    outdata = outdata[:remainder]
                    self.process(outdata)
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
            if module in self.modules:
                container = self.modules[module]
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
            self.help(full=True)
        elif command == "":
            pass
        else:
            print(f"Unrecognized command '{command}'.")
            self.help(full=False)

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


if __name__ == '__main__':
    engine = SynthEngine()
    engine.run()