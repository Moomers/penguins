#!/usr/bin/env python

import joystick, keyboard

inputlist = {
        'nes':{'description':'An NES controller', 'device':lambda device, **rest: joystick.Joystick(device, NESController())},
        'keyboard':{'description':'The keyboard arrow keys', 'device':lambda **rest: keyboard.Keyboard()},
        }
