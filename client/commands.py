#!/usr/bin/env python
"""Generic input events for penguin control."""

__author__ = 'Jered Wierzbicki'


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

class Horn(object):
    """Sound the horn."""
    pass

class Brake(object):
    """Push the brake."""
    pass

class Hold(object):
    """Drive with the same speed."""
    pass

class Reset(object):
    """Reset the controller."""
    pass

class Stop(object):
    """Puts the penguin into emergency stop."""
    pass

class Shutdown(object):
    """Shuts down the server."""
    pass

class Go(object):
    """Takes the penguin out of emergency stop."""
    pass

class Quit(object):
    """Quits the client."""
    pass
