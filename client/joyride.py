#!/usr/bin/env python
"""A dumb UI to let us drive with a joystick and get audio feedback."""

import commands
import joystick
import time
import threading

class JoyrideUI(threading.Thread):
    def __init__(self, joystick_device=None):
        threading.Thread.__init__(self)
        # used to stop the UI loop
        self._stop = threading.Event()
        if joystick_device is None:
            joystick_device = '/dev/input/js0'
        self.js = joystick.Joystick(joystick_device, joystick.NESController())

    def init(self):
        pass

    def run(self):
        while not self._stop.is_set():
            time.sleep(0.2)
        self.js.close()

    def get_command(self):
        return self.js.get_event()

    def update_status(self, status):
        pass

    def stop(self):
        self._stop.set()

    def error_notify(self, error):
        print error

def get_ui(**options):
    return JoyrideUI(joystick_device=options['joystick_device'])
