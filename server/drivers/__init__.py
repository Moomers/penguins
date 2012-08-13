#!/usr/bin/python

import smcserial, smcstub, smccmd, sabertooth

driverlist = {
        'sabertooth':('Talks to the Sabertooth 2x60 via the on-board arduino', sabertooth),
        }
