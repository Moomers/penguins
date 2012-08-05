#!/usr/bin/python

import smcserial, smcstub, smccmd, sabertooth

driverlist = {
        'smccmd':('Runs SmcCmd to process every request', smccmd),
        'smcserial':('Drives controllers using the serial protocol via a tty interface', smcserial),
        'smcstub':('Stub test driver for SMC controller-based drivers', smcstub),
        'sabertooth':('Talks to the Sabertooth 2x60 via the on-board arduino', sabertooth),
        }
