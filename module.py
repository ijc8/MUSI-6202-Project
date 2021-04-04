class Module:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
    
    def process(self, input_buffer, output_buffer):
        raise NotImplementedError