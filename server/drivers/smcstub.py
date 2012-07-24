#!/usr/bin/python

import common

class SMCStubController(object):
    """A fake SMC for interface testing."""
    def __init__(self, port):
        self._port = port
        self._speed = 0
        self._brake = 0
        self._safe = True

    @property
    def status(self):
        print '%s: status()' % self._port
        status = {
                'product':'stub',
                'firmware':'1.00',
                'errors': dict((cond, False) for cond in
                               common.SMCControllerErrors.values()),

                'speed':self.speed,
                'braking':self._brake,
                }

        if self._safe:
            status['errors']['safe start violation'] = True

        return status


    def reset(self):
        print '%s: reset()' % self._port
        self.speed = 0
        self._safe = False

    def stop(self):
        print '%s: stop()' % self._port
        self._safe = True
        self.speed = 0

    def brake(self, accel):
        print '%s: brake(%d)' % (self._port, accel)
        self._brake = accel

    def get_speed(self):
        print '%s: get_speed() = %d' % (self._port, self._speed)
        return self._speed

    def set_speed(self, speed):
        print '%s: set_speed(%d)' % (self._port, speed)
        self._speed = speed

    speed = property(get_speed, set_speed)

def get_driver(left, right, **rest):
    """Utility function which returns a driver using the controllers defined here"""
    return common.SmcDriver(SMCStubController(left),
                            SMCStubController(right))
