#!/usr/bin/env python

import commands

class SteeringModel(object):
    def __init__(self, status):
        self.last_status = status

        self.acceleration = 5
        self.braking = 1
        self.turn_acceleration = 2

    def parse_user_command(self, command):
        """Turns the latest user command into speed instructions for the robot"""
        if type(command) == commands.Hold:
            return {
                    'left':self.last_status['driver']['target left'],
                    'right':self.last_status['driver']['target right']}

        elif type(command) == commands.Steer:
            speed = abs(command.direction)
            if command.direction < 0:  # steer left
                return {
                        'left':self.last_status['driver']['target left'] - self.turn_acceleration * speed,
                        'right':self.last_status['driver']['target right'] + self.turn_acceleration * speed}
            else:  # steer right
                return {
                        'left':self.last_status['driver']['target left'] + self.turn_acceleration * speed,
                        'right':self.last_status['driver']['target right'] - self.turn_acceleration * speed}

        elif type(command) == commands.Drive:
            left = command.speed * self.acceleration
            right = command.speed * self.acceleration
            return {
                    'left':self.last_status['driver']['target left'] + left,
                    'right':self.last_status['driver']['target right'] + right}

        elif type(command) == commands.Brake:
            return self.last_status['driver']['braking_speed'] + self.braking * command.speed

        else:
            raise Exception("invalid steering command")

    def update_status(self, status):
        self.last_status = status
