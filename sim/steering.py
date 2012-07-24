#!/usr/bin/env python 

import math
import numpy as np

INCH = 1.
FOOT = 12. * INCH

DT = 0.1  # Timestep (seconds).
R_WHEEL = 8. * INCH  # 8 inch wheel radius.
CART_WIDTH = 2.5 * FOOT
CART_LENGTH = 5. * FOOT

class Cart(object):
    def __init__(self, x, y, width, length):
        self.origin_x = x
        self.origin_y = y
        self.left_x = x - width/2
        self.left_y = y + length/2
        self.left_rpm = 0
        self.right_rpm = 0
        self.theta = 0
        self.width = width
        self.length = length

    def get_polygon(self, dx, dy):
        # Center of axle is always at width/2, height/2.
        hw, hl = self.width / 2., self.length / 2.
        rot = np.matrix([[math.cos(self.theta), -math.sin(self.theta)],
                         [math.sin(self.theta), math.cos(self.theta)]])
        corners = np.matrix([[-hw, hw,           hw,          -hw],
                             [  0,  0, -self.length, -self.length]])
        pts = rot * corners + [[self.left_x - dx],
                               [self.left_y - dy]]
        return pts.getT().tolist()

    def sense(self):
        pass

    def move(self, left_rpm, right_rpm):
        self.left_rpm = left_rpm
        self.right_rpm = right_rpm
        self.theta += ((right_rpm - left_rpm) / self.width) * DT
        v = 2 * math.pi * R_WHEEL * (self.left_rpm + self.right_rpm) / 2
        self.left_x += v * math.sin(self.theta) * DT
        self.left_y += -v * math.cos(self.theta) * DT
