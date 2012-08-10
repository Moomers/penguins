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

MAX_VEL = 100
ACCEL = 5
TURN_ACCEL = 5
DECAY = 0.94
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
    last_v_left, last_v_right = 0, 0
    v_left, v_right = 0, 0
    decay = True
    estop = False
    try:
        while True:
            time.sleep(0.01)
            status = penguin.status
            arduino_status = status['status']['arduino']
            if not estop and arduino_status['estop']:
                mixer.queue(sounds['ebrake'])
                estop = True
            elif estop and not arduino_status['estop']:
                mixer.queue(sounds['yay'])
                estop = False
            ev = js.get_event()
            if ev:
                if type(ev) == commands.Horn and ev.pressed:
                    mixer.queue(sounds['honk'])
                elif type(ev) == commands.Brake and ev.pressed:
                    mixer.queue(sounds['screech'])
                    # emergency stop for now
                    penguin.stop()
                elif type(ev) == commands.Drive:
                    if ev.speed == -1: # go forward
                       v_left += ACCEL
                       v_right += ACCEL
                       decay = False
                    elif ev.speed == 1: # reverse
                       v_left -= ACCEL
                       v_right -= ACCEL
                       decay = False
                    elif ev.speed == 0: # release button
                       decay = True
                elif type(ev) == commands.Steer:
                    if ev.direction == -1: # go left
                       v_left -= TURN_ACCEL
                       v_right += TURN_ACCEL
                    elif ev.direction == 1: # go right
                       v_left += TURN_ACCEL
                       v_right -= TURN_ACCEL
                elif type(ev) == commands.Reset and not ev.pressed:
                    # issue reset when the button is released.
                    penguin.reset()
            if decay:
               v_left *= DECAY
               v_right *= DECAY
            if v_left < -MAX_VEL: v_left = -MAX_VEL
            if v_right < -MAX_VEL: v_right = -MAX_VEL
            if v_left > MAX_VEL: v_left = MAX_VEL
            if v_right > MAX_VEL: v_right = MAX_VEL
            if v_left != last_v_left:
               penguin.left = int(v_left)
            if v_right != last_v_right:
               penguin.right = int(v_right)
            if abs(v_left) < 1: v_left = 0
            if abs(v_right) < 1: v_right = 0
            print v_left, v_right
            last_v_right = v_right
            last_v_left = v_left
    except KeyboardInterrupt:
        pass
    js.close()
    mixer.stop()
    return 0

if __name__ == '__main__':
    sys.exit(main())
