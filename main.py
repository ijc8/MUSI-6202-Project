import sounddevice as sd
from example_module import ExampleModule

def callback(outdata, frames, time, status):
    module.process(outdata)

with sd.OutputStream(channels=1, callback=callback) as stream:
    module = ExampleModule(stream.samplerate)
    try:
        while stream.active:
            sd.sleep(1000)
    except KeyboardInterrupt:
        pass

