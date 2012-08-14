#!/usr/bin/env python

class SteeringModel(object):
    def __init__(self, status):
        self.last_status = status

        self.max_speed = 100
        self.acceleration = 5
        self.turn_acceleration = 2

    def parse_user_command(self, command):
        """Turns the latest user command into speed instructions for the robot"""
        if command[0] == 'hold':
            return {
                    'left':self.last_status['driver']['target left'],
                    'right':self.last_status['driver']['target right']}

        elif command[0] == 'left':
            speed = float(command[1])
            return {
                    'left':self.last_status['driver']['target left'] - self.turn_acceleration * speed,
                    'right':self.last_status['driver']['target right'] + self.turn_acceleration * speed}

        elif command[0] == 'right':
            speed = float(command[1])
            return {
                    'left':self.last_status['driver']['target left'] + self.turn_acceleration * speed,
                    'right':self.last_status['driver']['target right'] - self.turn_acceleration * speed}

        elif command[0] in ('forward', 'back'):
            if command[0] == 'forward':
                mult = 1
            else:
                mult = -1

            left_accel, speed_accel, right_accel = (
                    float(command[1][0]),
                    float(command[1][1]),
                    float(command[1][2]))

            left = mult * self.acceleration * float(command[1][1]) + self.turn_acceleration * left_accel
            right = mult * self.acceleration * float(command[1][1]) + self.turn_acceleration * right_accel

            return {
                    'left':self.last_status['driver']['target left'] + left,
                    'right':self.last_status['driver']['target right'] + right}

        else:
            raise Exception("invalid steering command")

    def update_status(self, status):
        self.last_status = status
