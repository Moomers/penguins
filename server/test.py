#!/usr/bin/python

left = '3000-6A06-3142-3732-7346-2543'
right = '3000-6F06-3142-3732-4454-2543'
smcpath = '/root/pololu/smc_linux/SmcCmd'

from drivers.smccmd import SmcCmdDriver
d = SmcCmdDriver(left, right, smcpath)
print "speeds -- left: %s\tright: %s" % (d.left, d.right)

