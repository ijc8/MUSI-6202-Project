Run:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 main.py

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
    > set delay.preset chorus
    > render 10 foo.wav
    File 'foo.wav' already exists. Overwrite? [y/N] y
    100.00% [==================================================]  10.00/44100.00
    Rendered 10.00s to 'foo.wav' in 5.86s (1.71x).

You may see warnings about underruns, but these should stop after a few seconds.