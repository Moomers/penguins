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
        self.log_slowdown = True
        self.log_control_estop = True
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

            # slow down to emergency speed if client hasn't issued control commands
            # for a while and is trying to go faster than this.
            # the driver is responsible for decelerating smoothly.
            if (self.control_age() > 2.5 and
                (self.robot.driver.status['target left'] > 10 or
                 self.robot.driver.status['target right'] > 10)):
                if self.log_slowdown:
                    logging.error('controlled slowdown; control_age %.4f' % (
                            self.control_age(),))
                self.robot.driver.set_speed(10)
                self.log_slowdown = False
            # emergency brake if still no control.
            elif self.control_age() > 5:
                if self.log_control_estop:
                    logging.error('controlled estop; control_age %.4f' % (
                        self.control_age(),))
                self.log_control_estop = False
                self.robot.driver.stop()
            else:
                self.log_slowdown = True
                self.log_control_estop = True


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


