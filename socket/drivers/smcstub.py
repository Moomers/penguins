#!/usr/bin/python

import common

class SimpleMotorController(object):
    """A fake SMC for interface testing."""
    def __init__(self, port):
        self._port = port
        self._speed = 0

    @property
    def status(self):
        print '%s: status()' % self._port
        status = {
                'product':'stub',
                'firmware':'1.00',
                'errors': dict((cond, False) for cond in
                               common.ControllerError.STATUS.values()),
                'speed':self.speed,
                }


    def reset(self):
        print '%s: reset()' % self._port
        pass

    def stop(self):
        print '%s: stop()' % self._port
        self.speed = 0

    def brake(self, accel):
        print '%s: brake(%d)' % (self._port, accel)
        pass

    def get_speed(self):
        print '%s: get_speed() = %d' % (self._port, self._speed)
        return self._speed

    def set_speed(self, speed):
        print '%s: set_speed(%d)' % (self._port, speed)
        self._speed = speed

    speed = property(get_speed, set_speed)

def get_driver(left_id, right_id):
    """Utility function which returns a driver using the controllers defined here"""
    return common.SmcDriver(SimpleMotorController(left_id),
                            SimpleMotorController(right_id))
