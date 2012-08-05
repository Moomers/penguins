#!/usr/bin/env python
"""Generic input events for penguin control."""

__author__ = 'Jered Wierzbicki'


class Horn(object):
    """Push the horn."""

    def __init__(self, pressed=False):
        self.pressed = pressed

    def __repr__(self):
        return 'Horn(pressed=%d)' % self.pressed


class Brake(object):
    """Push the brake."""

    def __init__(self, pressed=False):
        self.pressed = pressed

    def __repr__(self):
        return 'Brake(pressed=%d)' % self.pressed


class Steer(object):
    """Steer left or right."""

    def __init__(self, direction=0):
        """direction is between -1 for left and 1 for right."""
        self.direction = direction

    def __repr__(self):
        return 'Steer(direction=%.4f)' % self.direction


class Drive(object):
    """Drive with a certain speed."""

    def __init__(self, speed=0):
        """speed is between -1 for full reverse and 1 for full ahead."""
        self.speed = speed

    def __repr__(self):
        return 'Drive(speed=%.4f)' % self.speed


class Reset(object):
    """Reset the controller."""

    def __init__(self, pressed=False):
        self.pressed = pressed

    def __repr__(self):
        return 'Reset(pressed=%d)' % self.pressed
