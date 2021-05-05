Run:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 main.py

Requirements:
- There are two kinds of synth engines (subtractive and granular). The mix can be controlled with `set mixer.mix <value between 0 and 1>`.
- There is a CLI (and only a CLI).
- There is a fixed, well-defined signal chain (see `SynthEngine.__init__` inside `main.py`)
- Three modulated effects: auto-wah, tremolo, modulated delay-line with feedback (load presets with `set delay.preset <chorus, vibrato, flanger...>`).
- Convolution-based filtering. (Automated FIR filter design via Parks-McClellan.)
- Several filters: SVF, FIR (as described above), and an LPF emulating the classic Moog ladder filter. There are multiple instances of the SVF (as submodules of the subtractive synth and auto-wah).
  Filters may be visualized with `plot <filter module>`.
- All modules have a `mix` parameter controlling the balance between wet and dry.
- Input musical data via `midi connect` (run `midi list` to see devices) or `midi file`.
- Audio output is streaming by default (run `start`), may optionally be recorded live (`record`) or rendered (`render`).
- Output sample rate and bit depth are configurable. `set engine.samplerate <value>` and `set quantizer.depth <value>`, respectively.

Run `help` to see all available parameters and their current settings.

**NOTE:** Most modules are turned off at the start to simplify confirmation that audio output is working. Turn them on with `set <module name>.mix 1`.

Example interaction:

    $ python main.py
    Setup: internal sample rate = 48000, external sample rate = 44100
    > start
    > get subtractive.freq
    55
    > set subtractive.cutoff 400
    > set subtractive.freq 300
    > set subtractive.resonance 2
    > set subtractive.source square
    > set engine.samplerate 22050
    > set engine.samplerate 8000
    > set engine.samplerate 1000
    > set engine.samplerate 44100
    > set delay.mix 1
    > set delay.preset chorus
    > render 10 foo.wav
    File 'foo.wav' already exists. Overwrite? [y/N] y
    100.00% [==================================================]  10.00/10.00
    Rendered 10.00s to 'foo.wav' in 5.86s (1.71x).

You may see warnings about underruns, but these should stop after a few seconds.