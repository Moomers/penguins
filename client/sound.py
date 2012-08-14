#!/usr/bin/env python
"""Functionality to play sounds in response to events"""

import os
import pyaudio
import Queue
import threading
import wave

SOUND_DIR = '../sounds/joyride'

class Sound(object):
    def __init__(self, name):
        self.wf = wave.open(os.path.join(SOUND_DIR, name + '.wav'), 'rb')

SOUNDS = dict((name, Sound(name))
              for name in ['ebrake', 'honk', 'yay', 'screech',
                           'tada', 'uhoh', 'smb_bump', 'smb_warning',
                           'hothothot', 'relief'])

class Mixer(threading.Thread):
    CHUNKSIZE = 1024

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self._queue = Queue.Queue(0)
        self.pyaudio = pyaudio.PyAudio()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        self.pyaudio.terminate()

    def run(self):
        while not self._stop.isSet():
            try:
                sound = self._queue.get(block=False, timeout=0.1)
                self._play(sound)
            except Queue.Empty:
                pass

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

class SoundPlayer(object):
    def __init__(self, status):
        self.last_status = status
        self.mixer = Mixer()

    def start(self):
        self.mixer.start()

    def stop(self):
        self.mixer.stop()
        self.mixer.join()

    def update_status(self, new_status):
        """Go through the new status and play sounds for any new alerts"""
        self.last_status = new_status

if __name__ == "__main__":
    mixer = Mixer()
    mixer.start()
    mixer.queue(SOUNDS['tada'])
    mixer.stop()
