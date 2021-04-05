Run:

    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 main.py

Example interaction:

    $ python main.py
    > get subtractive.freq
    55
    > set subtractive.cutoff 400
    > set subtractive.freq 300
    > set subtractive.resonance 2
    > set subtractive.source "square"

You may see warnings about underruns, but these should stop after a few seconds.