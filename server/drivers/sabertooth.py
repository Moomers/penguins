#!/usr/bin/python

import common

class SabertoothDriver(object):
    """A driver which controls motors via the Sabertooth 2x60 Motor Controller"""

    def __init__(self, robot):
        self.robot = robot
        self.speeds = (0, 0)

    def _convert_speed(self, speed):
        """We want to specify speeds from 0 to 100, but the sabertooth uses 0 to 63"""
        if speed > 100 or speed < -100:
            raise common.DriverError("Speed outside the allowed range")

        return speed * 63 / 100

    ###### the interface of the driver #####
    def go(self):
        """Puts the controller into a basic run state"""
        self.robot.arduino.send_command('R')

    def stop(self):
        """Stops the robot"""
        self.robot.arduino.send_command('X')

    def brake(self, speed):
        """Applies braking to the motors"""
        self.speed = 0

    def set_speed(self, speed, motor = 'both'):
        """sets the speed of one or both motors"""
        #easily handle setting both or a single motor
        old_left, old_right = self.speeds
        speed = self._convert_speed(speed)
        if motor == 'both':
            self.speeds = (speed, speed)
        elif motor == 'left':
            self.speeds = (speed, old_right)
        elif motor == 'right':
            self.speeds = (old_left, speed)

        self.robot.arduino.send_command('V%d,%d' % (self.right, self.left))

    def get_speed(self, motor = 'both'):
        """Returns the current speed of a motor"""
        if motor == 'both':
            return list(self.speeds)
        elif motor == 'left':
            return [self.speeds[0]]
        elif motor == 'right':
            return [self.speeds[1]]

    speed = property(
            lambda self: self.get_speed('both'),
            lambda self, speed: self.set_speed(speed, 'both'))

    left = property(
            lambda self: self.get_speed('left')[0],
            lambda self, speed: self.set_speed(speed, 'left'))
    right = property(
            lambda self: self.get_speed('right')[0],
            lambda self, speed: self.set_speed(speed, 'right'))

    @property
    def status(self):
        return {
                'left':self.speeds[0],
                'right':self.speeds[1],
                }

def get_driver(robot, **rest):
    return SabertoothDriver(robot)
