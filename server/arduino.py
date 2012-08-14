#!/usr/bin/python

import copy
import logging
import os
import select
import serial
import threading
import time

from sensors import SensorReading

class State(object):
    """Represents the Arduino's current state."""

    def __init__(self,
            timestamp = time.time(),
            commands_sent = 0,
            commands_received = 0,
            bad_commands_received = 0,
            ms_since_command_received = 0,
            emergency_stop = False,
            ):
        self.timestamp = timestamp
        self.commands_sent = commands_sent
        self.commands_received = commands_received
        self.bad_commands_received = bad_commands_received
        self.ms_since_command_received = ms_since_command_received
        self.emergency_stop = emergency_stop

    def __repr__(self):
        return "State(timestamp=%f, commands_sent=%d, commands_received=%d, "\
                "bad_commands_received=%d, ms_since_command_received=%d, "\
                "emergency_stop=%d)" % (
                       self.timestamp,
                       self.commands_sent,
                       self.commands_received,
                       self.bad_commands_received,
                       self.ms_since_command_received,
                       self.emergency_stop)

class ArduinoMonitor(threading.Thread):
    """Monitors an Arduino state and sends regular heartbeat commands"""

    # Seconds between sending heartbeats.
    # The arduino estop timeout is 1 second, so with 0.1s between heartbeats
    # we get 10 attempts to keep it alive.
    HEARTBEAT_SECS = 0.1

    def __init__(self, arduino):
        """Initializes a serial monitor on an Arduino

        Args:
            arduino: the Arduino this monitor is monitoring
        """
        threading.Thread.__init__(self)

        self.arduino = arduino
        self.last_heartbeat_time = 0

        # used to stop the monitor thread
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            updated = self.arduino.update_state(self.HEARTBEAT_SECS)

            # Send a heartbeat if it is time.
            if time.time() - self.last_heartbeat_time >= self.HEARTBEAT_SECS:
                self.send_heartbeat()

        # remove reference to the arduino (for GC)
        self.arduino = None

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    def send_heartbeat(self):
        """Sends a heartbeat to make sure the serial link stays ok."""
        self.arduino.send_command('H')
        self.last_heartbeat_time = time.time()

class Arduino(object):
    """Represents an on-board arduino and provides a means of talking to it."""

    # Timeout for buffered serial I/O in seconds.
    IO_TIMEOUT_SEC = 5

    # how stale does the state get until we are considered no longer healthy?
    HEALTH_TIMEOUT = 2

    def __init__(self, port, baud_rate=9600):
        """Connects to the Arduino on a serial port.

        Args:
            port: The serial port or path to a serial device.
            baud_rate: The bit rate for serial communication.

        Raises:
            ValueError: There is an error opening the port.
            SerialError: There is a configuration error.
        """
        # Build the serial wrapper.
        self._serial = serial.Serial(port=port,
                baudrate=baud_rate, bytesize=8, parity='N', stopbits=1,
                timeout=self.IO_TIMEOUT_SEC, writeTimeout=self.IO_TIMEOUT_SEC)
        if not self._serial.isOpen():
            raise ValueError("Couldn't open %s" % port)

        # container for the internal state
        self.state = None
        self.sensor_readings = {}

        # How many commands we've sent to the Arduino.
        self.commands_sent = 0

        # used to make sure only a single thread tries to write to the arduino
        self.write_lock = threading.Lock()

        # the monitor ensures communication is still flowing
        self.monitor = ArduinoMonitor(self)

    def __del__(self):
        # There won't be a monitor if we failed to init the serial port.
        if hasattr(self, 'monitor'):
            self.stop()

    def is_healthy(self):
        """Returns True if our link with the Arduino is healthy."""
        # Not healthy until we've received a valid state.
        if not self.state:
            return False
        return (time.time() - self.state.timestamp < self.HEALTH_TIMEOUT)

    def start_monitor(self):
        """Starts the monitor thread that handles communication with the arduino"""
        if not self.monitor.is_alive():
            self.monitor.start()

    def stop(self):
        """Shuts down communication to the Arduino."""
        # shut down the monitor
        self.monitor.stop()
        self.monitor.join(timeout=5)

        # Maybe that worked, maybe it didn't. We're probably trying to reset
        # here, so just shut down hard and move on.
        if self.monitor.is_alive():
            logging.error('Monitor did not stop.')

        # close the serial port
        self._serial.close()

    @property
    def status(self):
        """Returns a dictionary of the arduino's status for the client"""
        status = {
                'healthy':self.is_healthy(),
                'estop':(not self.state or self.state.emergency_stop),
                'sent':self.commands_sent,
                'recieved':self.state.commands_received if self.state else 0,
                'bad':self.state.bad_commands_received if self.state else 0,
                }
        return status

    def send_command(self, command):
        """Sends a command to the Arduino.

        Args:
            command: An ASCII string which the controller will interpret.

        Returns:
            True if command was sent, False if something went wrong. Note
            this doesn't guarantee the command was actually received.
        """
        if not acquire(self.write_lock, 2):
            return False

        try:
            self._serial.write(command)
            if not command.endswith('\n'):
                self._serial.write('\n')
            self._serial.flush()
            self.commands_sent += 1
        finally:
            self.write_lock.release()

        return True

    def _read_data(self, timeout = None):
        """Reads a data line from the arduino"""
        if timeout is None:
            timeout = self.IO_TIMEOUT_SEC

        line = None

        # Wait for up to timeout seconds for data to become available.
        select.select([self._serial], [], [], timeout)
        if self._serial.inWaiting() != 0:
            line = self._serial.readline().strip()

        return line

    def _parse_data(self, data):
        """Parses the arduino raw arduino data into meaningful fields

        The protocol for the data the arduino sends back is:
            (State data)!(Sensor data)
        Each data area is broken up into fields like so:
            (Field name):(Field data);
        and fields are concatenated together with no spaces
        """
        def get_fields(data):
            """A helper function for splitting data into fields"""
            fields = {}
            for field in data.split(';'):
                k, v = field.split(':')
                fields[k] = v

            return fields

        state, sensors = data.split('!', 2)
        if not state.endswith(';') or not sensors.endswith(';'):
            return None

        state, sensors = get_fields(state.rstrip(';')), get_fields(sensors.rstrip(';'))
        return (state, sensors)

    def update_state(self, timeout = 0):
        """Updates the internal state with fresh data from the arduino"""
        try:
            state, sensors = self._parse_data(self._read_data(timeout))
            timestamp = time.time()

            # update the state
            new_state = State(
                    timestamp = timestamp,
                    commands_sent = self.commands_sent,
                    commands_received = int(state['C']),
                    bad_commands_received = int(state['B']),
                    ms_since_command_received = int(state['L']),
                    emergency_stop = bool(int(state['E'])),)
            self.state = new_state

            # update the new sensor readings
            for sensor_name, sensor_data in sensors.items():
                reading = SensorReading(timestamp, sensor_name, sensor_data)
                self.sensor_readings[sensor_name] = reading

        # failed to parse the state
        except:
            return False
        else:
            return True

    def get_state(self):
        """Returns a copy of the current state."""
        return copy.deepcopy(self.state)

    def get_sensor_reading(self, sensor_name):
        """Gets the raw data for a particular sensor"""
        try:
            reading = self.sensor_readings[sensor_name]
        except KeyError:
            return None
        else:
            return copy.deepcopy(reading)

class FakeArduino(object):
    """A fake arduino for when there's no real one"""
    def __init__(self):
        """Initializes a fake arduino"""
        self.state = State(emergency_stop = True)
        self.sensor_readings = {}

    def is_healthy(self):
        """Returns True if our link with the Arduino is healthy."""
        # Not healthy until we've received a valid state.
        return False

    def start_monitor(self):
        """Does nothing on this fake object"""
        pass

    def stop(self):
        """Does nothing on this fake object"""
        pass

    @property
    def status(self):
        """Returns a dictionary of the arduino's status for the client"""
        return {
                'healthy':self.is_healthy(),
                'estop':self.state.emergency_stop,
                'fake':True,
                }

    def send_command(self, command):
        """Increments the sent command count"""
        self.state.commands_sent += 1
        return True

    def _read_data(self, timeout = None):
        """Returns None"""
        return None

    def _parse_data(self, data):
        """Returns None"""
        return None

    def update_state(self, timeout = 0):
        """Updates the state timestamp"""
        self.state.timestamp = time.time()
        return True

    def get_state(self):
        """Returns a copy of the current state."""
        return copy.deepcopy(self.state)

    def get_sensor_reading(self, sensor_name):
        """Gets the raw data for a particular sensor"""
        try:
            reading = self.sensor_readings[sensor_name]
        except KeyError:
            return None
        else:
            return copy.deepcopy(reading)

def acquire(lock, timeout):
    """Acquire lock with a timeout"""
    if lock.acquire(False):
        return True

    start_time = time.time()
    while time.time() < start_time + timeout:
        if lock.acquire(False):
            return True
        time.sleep(.05)

    return False

def find_arduino(serial):
    """returns the first arduino found; if none found, returns a fake arduino"""
    arduinos = []

    for devname in [f for f in os.listdir('/dev') if f.startswith('ttyACM')]:
        try:
            desc = open('/sys/class/tty/%s/device/../product' % devname).read().strip().lower()
            if 'arduino' in desc:
               arduinos.append({
                   'name':devname,
                   'device':os.path.join('/dev', devname),
                   'serial':open('/sys/class/tty/%s/device/../serial' % devname).read().strip().lower(),
                   })
        except:
           continue

    # if a serial number is passed in always require a particular arduino
    if serial:
        matching = [a for a in arduinos if a['serial'] == serial]
        if len(matching) == 0:
            raise Exception("No arduino with serial number %s found" % serial)
        elif len(matching) > 1:
            raise Exception("Multiple arduinos with serial number %s found!" % serial)
        else:
            return Arduino(matching[0]['device'])

    # if no serial number passed, pick any old random arduino, including a fake one
    else:
        if len(arduinos) == 0:
            print "Warning: no arduino found; using fake arduino"
            return FakeArduino()
        else:
            if len(arduinos) > 1:
                print "Warning: multiple arduinos found! Using %s" % arduinos[0]['name']

            return Arduino(arduinos[0]['device'])

if __name__ == '__main__':
    a = find_arduino()
    try:
        while True:
            time.sleep(1)
            print a.get_state()
    finally:
        a.stop()
