#!/usr/bin/env python

import math
import pygame
import pygame.gfxdraw
import random
import steering
import sys

NUM_FOLLOWERS = 3
ZOOM = 10

class Checker(object):
    def __init__(self, width, height, n, color1, color2):
        self.width = width
        self.height = height
        self.n = n
        self.xstep = float(width) / n
        self.ystep = float(height) / n
        self.color1 = color1
        self.color2 = color2

    def draw(self, surface, xoffs, yoffs):
        xoffs = xoffs % (2*self.xstep)
        yoffs = yoffs % (2*self.ystep)
        for i in xrange(self.n+2):
            for j in xrange(self.n+2):
                x = self.xstep * i - xoffs
                y = self.ystep * j - yoffs
                color = self.color1 if (i & 1) != (j & 1) else self.color2
                rect = pygame.Rect(x, y, self.xstep, self.ystep)
                surface.fill(color, rect=rect)

def main():
    pygame.init()

    size = width, height = 800, 600
    screen = pygame.display.set_mode(size)
    white = 255, 255, 255
    dgray = 128, 128, 128
    lgray = 190, 190, 190
    black = 0, 0, 0

    bg = Checker(width, height, 20, dgray, lgray)
    cart = steering.Cart(width / 2, height / 2,
            steering.CART_WIDTH, steering.CART_LENGTH)
    followers = []
    space = 3 * NUM_FOLLOWERS * steering.CART_WIDTH
    for i in xrange(NUM_FOLLOWERS):
        followers.append(steering.Cart(
            width / 2 - space / 2 + (space / NUM_FOLLOWERS) * (i + 0.5),
            height / 2 + steering.CART_LENGTH * 3,
            steering.CART_WIDTH, steering.CART_LENGTH))
    rl, rr = 0, 0  # actual rpm
    drl, drr = 0, 0  # desired rpm
    s = 0  # driving speed
    t = 0.5  # turning speed
    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.unicode == 'h':
                    #drl, drr = t, -t
                    drl = drr + t
                elif event.unicode == 'j':
                    s -= 0.5
                    drl, drr = s, s
                elif event.unicode == 'k':
                    s += 0.5
                    drl, drr = s, s
                elif event.unicode == 'l':
                    #drl, drr = -t, t
                    drr = drl + t
                elif event.unicode == 'q':
                    done = True
        rr += (drr - rr) * 0.01
        rl += (drl - rl) * 0.01

        screen.fill(white)
        xoffs = (cart.left_x + cart.width/2) - width/2
        yoffs = (cart.left_y - cart.length/2) - height/2
        bg.draw(screen, xoffs/ZOOM, yoffs/ZOOM)
        cart.move(rl, rr)
        for f in followers:
            f.move(rl, rr)
        for f in followers:
            pygame.gfxdraw.aapolygon(screen, f.get_polygon(xoffs, yoffs), black)
        pygame.gfxdraw.aapolygon(screen, cart.get_polygon(xoffs, yoffs), black)
        pygame.display.flip()
    sys.exit()

if __name__ == '__main__':
    main()
