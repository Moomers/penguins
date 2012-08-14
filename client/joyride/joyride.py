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

LEFT_ADJUST = 1.1
RIGHT_ADJUST = 1

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


def collision_imminent(sensors):
    """Returns True if the sensors say we're about to hit something."""
    try:
        return (sensors['Left sonar']['value'] < 50 or
                sensors['Right sonar']['value'] < 50)
    except KeyError:
        return False


def battery_critical(sensors):
    """Returns True if we're critically low on battery."""
    try:
        return sensors['Battery voltage']['value'] < 20
    except KeyError:
        return False


def temp_critical(sensors, cur_critical):
    """Returns True if we're overtemperature."""
    try:
        if cur_critical:
            return sensors['Driver temperature']['value'] > 35
        else:
            return sensors['Driver temperature']['value'] > 50
    except KeyError:
        return False


class Quacker(object):
    """Makes noise when there is something interesting going on."""

    def __init__(self, mixer):
        self.mixer = mixer
        self.collision_imminent = False
        self.battery_critical = False
        self.last_battery_critical_notice = 0
        self.last_temp_critical_notice = 0
        self.temp_critical = False
        self.emergency_brake = False

    def update(self, status):
        arduino = status['arduino']
        sensors = dict((s['name'], s) for s in status['sensors'])
        new_collision_imminent = collision_imminent(sensors)
        new_battery_critical = battery_critical(sensors)
        new_temp_critical = temp_critical(sensors, self.temp_critical)
        if not self.emergency_brake and arduino['estop']:
            self.mixer.queue(SOUNDS['ebrake'])
            self.emergency_brake = True
        elif self.emergency_brake and not arduino['estop']:
            self.mixer.queue(SOUNDS['yay'])
            self.emergency_brake = False
        elif not self.collision_imminent and new_collision_imminent:
            self.mixer.queue(SOUNDS['smb_bump'])
            self.collision_imminent = True
        elif self.collision_imminent and not new_collision_imminent:
            self.collision_imminent = False
        elif not self.temp_critical and new_temp_critical:
            self.mixer.queue(SOUNDS['hothothot'])
            self.last_temp_critical_notice = time.time()
            self.temp_critical = True
        elif self.temp_critical and not new_temp_critical:
            self.mixer.queue(SOUNDS['relief'])
            self.temp_critical = False
        elif (self.temp_critical and
              time.time() - self.last_temp_critical_notice > 30):
            self.mixer.queue(SOUNDS['hothothot'])
            self.last_temp_critical_notice = time.time()
        elif (not self.battery_critical and new_battery_critical and
              time.time() - self.last_battery_critical_notice > 5*60):
            self.mixer.queue(SOUNDS['smb_warning'])
            self.last_battery_critical_notice = time.time()
            self.battery_critical = True
        elif self.battery_critical and not new_battery_critical:
            self.battery_critical = False


def main():
    penguin = client.DriverClient(client.HOST, client.PORT)
    mixer = Mixer()
    mixer.start()
    quacker = Quacker(mixer)
    js = joystick.Joystick('/dev/input/js0', joystick.NESController())
    mixer.queue(SOUNDS['tada'])
    last_v_left, last_v_right = 0, 0
    v_left, v_right = 0, 0
    decay = True
    exit_status = 0
    try:
        while True:
            time.sleep(0.01)
            quacker.update(penguin.status)
            ev = js.get_event()
            if ev:
                if type(ev) == commands.Horn and ev.pressed:
                    mixer.queue(SOUNDS['honk'])
                elif type(ev) == commands.Brake and ev.pressed:
                    mixer.queue(SOUNDS['screech'])
                    # emergency stop for now
                    penguin.stop()
                    v_left = 0
                    v_right = 0
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
            def clamp(vel):
                if vel < -MAX_VEL: return -MAX_VEL
                elif vel > MAX_VEL: return MAX_VEL
                return vel

            if decay:
               v_left *= DECAY
               v_right *= DECAY

            clamped_v_left = clamp(int(v_left * LEFT_ADJUST))
            clamped_v_right = clamp(int(v_right * RIGHT_ADJUST))

            if clamped_v_left != last_v_left:
               penguin.left = clamped_v_left
            if clamped_v_right != last_v_right:
               penguin.right = clamped_v_right

            # set the speed to 0 when it's really low
            if abs(v_left) < 3: v_left = 0
            if abs(v_right) < 3: v_right = 0

            #save previous speed
            last_v_right = clamped_v_right
            last_v_left = clamped_v_left

    except KeyboardInterrupt:
        mixer.queue(SOUNDS['uhoh'])
        time.sleep(0.5)
        exit_status = 2
    except Exception,e:
        print e
        # Somethins' busted, bail.
        mixer.queue(SOUNDS['uhoh'])
        # Give uhoh some time to happen.
        time.sleep(0.5)
        exit_status = 1
    js.close()
    mixer.stop()
    return exit_status

if __name__ == '__main__':
    sys.exit(main())
