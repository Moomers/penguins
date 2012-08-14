#!/usr/bin/python

import logging
import os
import time
import threading

def touch(fname, times = None):
    fhandle = file(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

class ServerMonitor(threading.Thread):
    """Monitors the server and robot and takes action on exceptional conditions"""
    def __init__(self, server, robot):
        threading.Thread.__init__(self)
        self.server = server
        self.robot = robot
        self.log_estop = True
        self.last_touched = 0

        # used to stop the monitor thread
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            for sensor in self.robot.sensors.values():
                sensor.read()

            # brake if the client hasn't said anything for a while
            if self.client_age() > 5:
                # print out this log message once per timeout
                if self.log_estop:
                    logging.error('monitor estop; client_age %.4f' % (
                        self.client_age(),))
                self.robot.driver.stop()
                self.log_estop = False
            else:
                self.log_estop = True

            # touch a file every so often to tell watchdog we're still here
            if time.time() - self.last_touched > 1:
                touch('/tmp/server-monitor-alive')
                self.last_touched = time.time()

            # send new robot speed
            self.robot.driver.update_speed()

            time.sleep(.05)

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    def client_age(self):
        """Time since last client request to the robot's server"""
        return round(time.time() - self.server.last_request, 2)

    def control_age(self):
        """Time since last control command to the robot"""
        return round(time.time() - self.robot.last_control, 2)

    @property
    def status(self):
        """Returns the monitor status"""
        status = {
                'client_age':self.client_age(),
                'control_age':self.control_age(),
                }

        return status


