#!/usr/bin/python

import time
import threading

class ServerMonitor(threading.Thread):
    """Monitors the server and takes action on exceptional conditions"""
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server

        # used to stop the monitor thread
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            for sensor in self.server.sensors.values():
                sensor.read()

            time.sleep(.05)

            # brake if the client hasn't said anything for a while
            if self.client_age() > 5:
                self.server.driver.stop()

        # remove reference to the arduino (for GC)
        self.arduino = None

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    def client_age(self):
        return round(time.time() - self.server.last_request, 1)

    @property
    def status(self):
        """Returns the monitor status"""
        status = {
                'client_age':self.client_age(),
                }

        return status


