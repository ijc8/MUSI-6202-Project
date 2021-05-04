import time

import mido

class MIDISource:
    def __init__(self):
        self.port = None

    def connect(self, callback, name=None):
        def _callback(message):
            if not message.is_meta and message.type == 'note_on':
                callback(message.note, message.velocity)
        self.port = mido.open_input(name, callback=_callback)
    
    def disconnect(self):
        if self.port:
            self.port.close()
            self.port = None