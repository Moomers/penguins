#!/usr/bin/env python
"""A dumb UI to let us drive with a joystick and get audio feedback."""

import commands
import client
import joystick
import time
import os
import pyaudio
import sys
import threading
import Queue
import wave

SOUND_DIR = '../sounds/joyride'

class Sound(object):
    def __init__(self, name):
        self.wf = wave.open(os.path.join(SOUND_DIR, name + '.wav'), 'rb')

class Mixer(threading.Thread):
    CHUNKSIZE = 1024

    def __init__(self):
        threading.Thread.__init__(self)
        self._queue = Queue.Queue(0)
        self.pyaudio = pyaudio.PyAudio()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        self.pyaudio.terminate()

    def run(self):
        while not self._stop.isSet():
            sound = self._queue.get()
            self._play(sound)

    def queue(self, sound):
        self._queue.put(sound)

    def _play(self, sound):
        stream = self.pyaudio.open(
            format=self.pyaudio.get_format_from_width(sound.wf.getsampwidth()),
            channels=sound.wf.getnchannels(),
            rate=sound.wf.getframerate(),
            output=True)
        stream.start_stream()
        sound.wf.rewind()
        data = sound.wf.readframes(Mixer.CHUNKSIZE)
        while data != '':
            stream.write(data)
            data = sound.wf.readframes(Mixer.CHUNKSIZE)
        stream.close()

def main():
    penguin = client.DriverClient(client.HOST, client.PORT)
    mixer = Mixer()
    mixer.start()
    sounds = dict((name, Sound(name))
                  for name in ['bing', 'ebrake', 'honk', 'yay', 'screech'])
    js = joystick.Joystick('/dev/input/js0', joystick.NESController())
    vleft, vright = 0, 0
    estop = False
    try:
        while True:
            time.sleep(0.01)
            try:
                status = penguin.status()
                if not estop and status['ardunio']['estop']:
                    mixer.queue(sounds['ebrake'])
                    estop = True
                elif estop and not status['arduino']['estop']:
                    mixer.queue(sounds['yay'])
                    estop = False
            except:
                pass
            if js.has_events():
                ev = js.pop_event()
                if type(ev) == commands.Horn and ev.pressed:
                    mixer.queue(sounds['honk'])
                elif type(ev) == commands.Brake and ev.pressed:
                    mixer.queue(sounds['screech'])
                elif type(ev) == commands.Reset and not ev.pressed:
                    # issue reset when the button is released.
                    penguin.reset()
    except KeyboardInterrupt:
        pass
    js.close()
    mixer.stop()
    return 0

if __name__ == '__main__':
    sys.exit(main())
