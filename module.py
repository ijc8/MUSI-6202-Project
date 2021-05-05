class Module:

    PARAMETERS = ("mix",)

    def __init__(self, sample_rate, mix=1):
        self.sample_rate = sample_rate
        self.mix = mix
    
    def process(self, input_buffer, output_buffer):
        raise NotImplementedError