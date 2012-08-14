#!/usr/bin/python

import common
from math import copysign
import time

class SabertoothDriver(object):
    """A driver which controls motors via the Sabertooth 2x60 Motor Controller"""
    def __init__(self, robot,
            min_speed = 0, max_speed = 100, max_braking = 100, max_acceleration = 200, max_turn_speed = 200,
            speed_adjust = 1, left_speed_adjust = 1, right_speed_adjust = 1,
            min_update_interval = 0.1):
        self.robot = robot

        # validate and save parameters
        # these parameters cause new values to be rejected (checked in set_speed)
        self.max_speed = self.validate_parameter('Maximum speed', max_speed, 1, 100)
        self.max_turn_speed = self.validate_parameter('Maximum turn speed', max_turn_speed, 1, 200)

        # these parameters control the functioning of the driver (checked in update_speed)
        self.min_speed = self.validate_parameter('Minimum speed', min_speed, 0, 99)
        self.max_acceleration = self.validate_parameter('Maximum acceleration', max_acceleration, 1, 200)
        self.speed_adjust = self.validate_parameter('Overall speed adjustment', speed_adjust, 0, 1)

        self.side_adjust = (
                self.validate_parameter('Left speed adjustment', left_speed_adjust, 0, 1),
                self.validate_parameter('Right speed adjustment', right_speed_adjust, 0, 1))

        # controls maximum frequency with which update_speed runs
        self.last_speed_update = 0  # last time speed was updated
        self.min_update_interval = min_update_interval

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
        self.target_speeds = [0, 0]
        self.robot.arduino.send_command('G')

    def stop(self):
        """Stops the robot"""
        self.robot.arduino.send_command('X')
        self.target_speeds = [0, 0]

    def brake(self, speed):
        """Applies braking to the motors"""
        self.target_speed = [0, 0]

    def set_speed(self, speed, motor = 'both'):
        """sets the target speed of one or both motors"""
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
        to_send = list(self.last_speeds)

        for i in (0, 1):
            # if our speed is too slow, send 0 but claim target has been reached
            if abs(target_speeds[i]) < self.min_speed:
                self.last_speeds[i] = copysign(self.min_speed, target_speeds[i])
                to_send[i] = 0

            else:
                # avoid accelerating more than the max acceleration
                diff = target_speeds[i] - self.last_speeds[i]
                if abs(diff) > self.max_acceleration:
                    diff = copysign(self.max_acceleration, diff)
                self.last_speeds[i] = self.last_speeds[i] + diff

                # send adjusted parameters
                to_send[i] = self.last_speeds[i] * self.side_adjust[i] * self.speed_adjust

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
                'last_right':self.last_speeds[1],
                'last_speed_update':self.last_speed_update,
                }

def get_driver(robot, **rest):
    return SabertoothDriver(robot)
