#!/usr/bin/env python
"""Functionality to play sounds in response to events"""

import glob
import os
import pyaudio
import Queue
import threading
import time
import wave

class Sound(object):
    def __init__(self, path):
        self.wf = wave.open(path, 'rb')

class Mixer(threading.Thread):
    CHUNKSIZE = 1024

    def __init__(self):
        threading.Thread.__init__(self, name = 'player_mixer')
        self.setDaemon(True)
        self._queue = Queue.Queue(0)
        self.pyaudio = pyaudio.PyAudio()
        self._stop = threading.Event()

    def stop(self, final_sound = None):
        self._stop.set()
        self.join()
        if final_sound:
            self._play(final_sound)

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
    SOUNDS = dict((os.path.basename(name)[:-4], Sound(name))
                  for name in glob.glob('../sounds/*.wav'))

    def __init__(self, status):
        self.last_status = status
        self.mixer = Mixer()

    def start(self):
        self.mixer.start()

    def play(self, sound):
        self.mixer.queue(sound)

    def stop(self, final_sound = None):
        self.mixer.stop(final_sound)
        self.mixer.join()

    def update_status(self, new_status):
        """Go through the new status and play sounds for any new alerts"""
        def became_set(key, old, new): return not old[key] and new[key]
        def became_cleared(key, old, new): return old[key] and not new[key]

        old, new = self.last_status['arduino'], new_status['arduino']
        if became_set('estop', old, new):
            self.mixer.queue(self.SOUNDS['estop'])
        elif became_cleared('estop', old, new):
            self.mixer.queue(self.SOUNDS['clear_estop'])
        if became_set('healthy', old, new):
            self.mixer.queue(self.SOUNDS['arduino_healthy'])
        elif became_cleared('healthy', old, new):
            self.mixer.queue(self.SOUNDS['arduino_unhealthy'])

        old, new = self.last_status['monitor']['alerts'], new_status['monitor']['alerts']
        if became_set('Driver overtemp estop', old, new):
            self.mixer.queue(self.SOUNDS['driver_estop_set'])
        elif became_cleared('Driver overtemp estop', old, new):
            self.mixer.queue(self.SOUNDS['driver_estop_clear'])
        if became_set('Driver overtemp warn', old, new):
            self.mixer.queue(self.SOUNDS['driver_warn'])
        if became_set('Battery estop', old, new):
            self.mixer.queue(self.SOUNDS['battery_estop_set'])
        elif became_cleared('Battery estop', old, new):
            self.mixer.queue(self.SOUNDS['battery_estop_clear'])
        if became_set('Battery warn', old, new):
            self.mixer.queue(self.SOUNDS['battery_warn'])
        if became_set('Sonar warn', old, new):
            self.mixer.queue(self.SOUNDS['sonar_warn'])
        if became_set('Encoder warn', old, new):
            pass
            #self.mixer.queue(self.SOUNDS['encoder_warn'])

        self.last_status = new_status

if __name__ == "__main__":
    mixer = Mixer()
    mixer.start()
    mixer.queue(SoundPlayer.SOUNDS['startup'])
    time.sleep(2)
    mixer.stop()
