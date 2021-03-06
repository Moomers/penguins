#!/usr/bin/python

import common
from math import copysign
import time

from parameters import driver as dp

class SabertoothDriver(object):
    """A driver which controls motors via the Sabertooth 2x60 Motor Controller"""
    def __init__(self, robot,
            min_speed = 0, max_speed = 100, max_turn_speed = 200, max_acceleration = 100, max_braking = 100,
            speed_adjust = 1, left_speed_adjust = 1, right_speed_adjust = 1,
            min_update_interval = 0.1, **rest):
        self.robot = robot

        # validate and save parameters
        # these parameters cause new values to be rejected (checked in set_speed)
        self.max_speed = self.validate_parameter('Maximum speed', max_speed, 1, 100)
        self.max_turn_speed = self.validate_parameter('Maximum turn speed', max_turn_speed, 1, 200)

        # these parameters control the functioning of the driver (checked in update_speed)
        self.min_speed = self.validate_parameter('Minimum speed', min_speed, 0, 99)
        self.max_acceleration = self.validate_parameter('Maximum acceleration', max_acceleration, 1, 200)
        self.max_braking = self.validate_parameter('Maximum braking speed', max_braking, 1, 200)
        self.speed_adjust = self.validate_parameter('Overall speed adjustment', speed_adjust, 0, 1)

        self.side_adjust = (
                self.validate_parameter('Left speed adjustment', left_speed_adjust, 0, 1),
                self.validate_parameter('Right speed adjustment', right_speed_adjust, 0, 1))

        # controls maximum frequency with which update_speed runs
        self.last_speed_update = 0  # last time speed was updated
        self.min_update_interval = min_update_interval

        # controls braking mode
        self.braking_speed = 0

        self.target_speeds = [0, 0] # target speed (set by calls to set_speed)
        self.last_speeds = [0, 0]   # last speed sent to motor controller (before adjust)

    def validate_parameter(self, name, value, minimum, maximum):
        if value >= minimum and value <= maximum: return value
        else: raise ValueError("%s must be between %s and %s" % (name, minimum, maximum))

    def _convert_speed(self, speed):
        """We want to specify speeds from 0 to 100, but the sabertooth uses 0 to 63"""
        if speed > 100 or speed < -100:
            raise common.DriverError("Speed outside the allowed range")

        return int(speed * 63 / 100)

    ###### the interface of the driver #####
    def go(self):
        """Puts the controller into a basic run state"""
        self.brake(self.max_braking)
        self.robot.arduino.send_command('G')

    def stop(self):
        """Stops the robot"""
        self.robot.arduino.send_command('X')
        self.target_speeds = [0, 0]

    def brake(self, speed):
        """Applies braking to the motors"""
        if speed < 0:
            raise common.ParameterError("Braking speed %d cannot be negative" % speed)
        elif speed > self.max_braking:
            raise common.ParameterError("Braking speed %d exceeds maximum value of %d" % (speed, self.max_braking))

        self.target_speeds = [0,0]
        self.braking_speed = speed

    def set_speed(self, speed, motor = 'both'):
        """sets the target speed of one or both motors"""
        if self.robot.arduino.status['estop']:
            raise common.StoppedError("Cannot change speed while emergency stopped")

        old_left, old_right = self.target_speeds

        # figure out what new targets will be
        if motor == 'both':
            new_left, new_right = (speed, speed)
        elif motor == 'left':
            new_left, new_right = (speed, old_right)
        elif motor == 'right':
            new_left, new_right = (old_left, speed)

        # validate new targets
        if abs(speed) > self.max_speed:
            raise common.ParameterError("Speed %d exceeds maximum value of %d" % (speed, copysign(self.max_speed, speed)))

        if abs(new_left - new_right) > self.max_turn_speed:
            raise common.ParameterError("New targets (%d,%d) exceed maximum turn velocity of %d" % (new_left, new_right, self.max_turn_speed))

        # we're good -- update the speed
        self.braking_speed = 0
        self.target_speeds = [new_left, new_right]

    def update_speed(self):
        """Updates the current speed to match target speed (in accordance with parameters)"""
        # if it's too soon since we last ran, exit
        if (time.time() - self.last_speed_update) < self.min_update_interval:
            return False

        # if we have nothing to do, we're done
        if self.target_speeds == self.last_speeds:
            return True

        # make a copy of the target spees to avoid race conditions
        target_speeds = list(self.target_speeds)

        # figure out what we're going to send this time around
        to_send = list(target_speeds)
        for i in (0, 1):
            # what is our maximum acceleration speed?
            # if we're actively braking, we can change at up to brake speed
            # never use braking to accelerate though; in that case, use
            # normal acceleration model
            if self.braking_speed and abs(target_speeds[i]) < abs(self.last_speeds[i]):
                max_diff = self.braking_speed
            # otherwise we're accelerating/decellerating normally
            else:
                max_diff = self.max_acceleration

            # avoid accelerating more than the max acceleration
            diff = target_speeds[i] - self.last_speeds[i]
            if abs(diff) > max_diff:
                diff = copysign(max_diff, diff)

            # figure out new speed to send
            self.last_speeds[i] = self.last_speeds[i] + diff

            # send adjusted parameters
            to_send[i] = self.last_speeds[i] * self.side_adjust[i] * self.speed_adjust

        # if our speed is too slow, send 0 but claim target has been reached
        for i in (0,1):
            if abs(to_send[i]) < self.min_speed:
                self.last_speeds[i] = target_speeds[i]
                to_send[i] = 0

        # sabertooth takes right,left instead of left-right like everything else here
        self.robot.arduino.send_command('V%d,%d' % (
            self._convert_speed(to_send[1]),
            self._convert_speed(to_send[0])))

        self.last_speed_update = time.time()

    @property
    def status(self):
        return {
                'target left':self.target_speeds[0],
                'target right':self.target_speeds[1],
                'last left':self.last_speeds[0],
                'last right':self.last_speeds[1],
                'last speed update':self.last_speed_update,
                'braking speed':self.braking_speed,
                }

def get_driver(robot, **rest):
    args = dict(dp)
    args['robot'] = robot
    return SabertoothDriver(**args)
