#!/usr/bin/python

import time
import threading

class ServerMonitor(threading.Thread):
    """Monitors the server and takes action on exceptional conditions"""
    def __init__(self, server):
        self.server = server

        # used to stop the monitor thread
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            time.sleep(.1)

        # remove reference to the arduino (for GC)
        self.arduino = None

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    @property
    def status(self):
        """Returns the monitor status"""
        status = {
                'client_age':(time.time() - self.server.last_request ),
                }
        return status


