#!/usr/bin/env python

class SteeringModel(object):
    def __init__(self, status):
        self.last_status = status

    def parse_user_command(self, command):
        """Turns the latest user command into speed instructions for the robot"""
        pass

    def update_status(self, status):
        self.last_status = status
