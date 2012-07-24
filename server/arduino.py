#!/usr/bin/python

import copy
import logging
import select
import serial
import threading
import time

# Some nicer constants for abbreviated sensor names.
LEFT_POT = 'LP'
RIGHT_POT = 'RP'
LEFT_SONAR = 'LS'
RIGHT_SONAR = 'RS'
AMG_SENSOR = 'AMG'


class AmgReading(object):
    """A reading from a 3D orientation sensor."""

    def __init__(self, value):
        mags = [int(mag) for mag in value.split(',', 9)]
        self.ax, self.ay, self.az = mags[:3]
        self.mx, self.my, self.mz = mags[3:6]
        self.gx, self.gy, self.gz = mags[6:]

    def __repr__(self):
        return "AmgReading('%s')" % ','.join(
                str(s) for s in (self.ax, self.ay, self.az,
                    self.mx, self.my, self.mz,
                    self.gx, self.gy, self.gz))


class PotReading(object):
    """A reading from a potentiometer for steering control."""

    def __init__(self, value):
        # TODO: Normalize the range.
        self.value = int(value)

    def __repr__(self):
        return "PotReading(%d)" % self.value


class SonarReading(object):
    """A reading from an ultrasound distance sensor."""

    def __init__(self, distance):
        self.distance = int(distance)

    def __repr__(self):
        return "SonarReading(%d)" % self.distance


# The type of value each sensor produces.
SENSORS = {
    LEFT_POT: PotReading,
    RIGHT_POT: PotReading,
    LEFT_SONAR: SonarReading,
    RIGHT_SONAR: SonarReading,
    AMG_SENSOR: AmgReading,
}


class SensorData(object):
    """Data from on-board sensors."""

    def __init__(self, values=None):
        self.values = values

    @staticmethod
    def parse(values):
        """Parses sensor data from raw values.

        Args:
            values: A dict with raw sensor readings from the Arduino.

        Returns:
            A SensorData object.

        Raises:
            ValueError: If some sensor readings did not parse.
            KeyError: If an invalid sensor name is specified.
        """
        parsed_values = {}
        for name in values.keys():
            parsed_values[name] = SENSORS[name](values[name])
        return SensorData(parsed_values)

    def get(self, name):
        """Returns a reading from the named sensor."""
        return self.values[name]

    def __repr__(self):
        return "SensorData(%s)" % str(self.values)


class State(object):
    """Represents the Arduino's current state."""

    def __init__(self, commands_received=0, bad_commands_received=0,
                 loops_since_command_received=0, emergency_stop=False,
                 sensor_data=None):
        self.timestamp = time.time()
        self.commands_received = commands_received
        self.bad_commands_received = bad_commands_received
        self.loops_since_command_received = loops_since_command_received
        self.emergency_stop = emergency_stop
        self.sensor_data = sensor_data

    def __repr__(self):
        return "State(commands_received=%d, bad_commands_received=%d, "\
               "loops_since_command_received=%d, emergency_stop=%d, "\
               "sensor_data=%s)" % (
                       self.commands_received,
                       self.bad_commands_received,
                       self.loops_since_command_received,
                       self.emergency_stop,
                       self.sensor_data)

    @staticmethod
    def parse(line):
        """Parses a state line.

        Returns:
            A State object or None if the line is not well-formed."""
        def get_groups(data):
            groups = {}
            for group in data.split(';'):
                k, v = group.split(':')
                groups[k] = v

            return groups

        line = line.strip()
        try:
            state, sensors = line.split('!', 2)
            if not state.endswith(';') or not sensors.endswith(';'):
                return None
            state, sensors = get_groups(state[:-1]), get_groups(sensors[:-1])
            return State(commands_received=int(state['C']),
                         bad_commands_received=int(state['B']),
                         loops_since_command_received=int(state['L']),
                         emergency_stop=bool(int(state['E'])),
                         sensor_data=SensorData.parse(sensors))
        except:
            # The state line did not parse correctly.
            return None

    def get_timestamp(self):
        return self.timestamp

    def get_commands_received(self):
        return self.commands_received

    def get_bad_commands_received(self):
        return self.bad_commands_received

    def get_loops_since_command_received(self):
        return self.loops_since_command_received

    def get_emergency_stop(self):
        return self.emergency_stop

    def get_sensor_reading(self, name):
        if self.sensor_data:
            return self.sensor_data.get(name)
        return None


class SerialMonitor(threading.Thread):
    """Monitors state and sends a heartbeat to the Arduino serial port."""

    # Seconds between sending heartbeats.
    HEARTBEAT_SECS = 5

    def __init__(self, serial, write_lock):
        """Initializes the serial monitor.

        Args:
            serial: A serial.Serial object shared with the Arduino.
            write_lock: A threading.Lock to share write access to serial.
        """
        threading.Thread.__init__(self)

        self.serial = serial
        self.last_heartbeat_time = 0
        self.write_lock = write_lock
        self.healthy = False
        self.state = None
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            # Wait for up to HEARTBEAT_SECS for data to become available.
            select.select([self.serial], [], [], self.HEARTBEAT_SECS)
            if self.serial.inWaiting() != 0:
                # The Arduino has started sending something.
                line = self.serial.readline()
                state = State.parse(line)
                if state:
                    # State parsed, so we are healthy.
                    self.healthy = True
                    # Save the new valid state.
                    self.state = state

            if time.time() - self.last_heartbeat_time >= self.HEARTBEAT_SECS:
                # Send a heartbeat if it is time.
                self.send_heartbeat()

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    def is_healthy(self):
        """Returns True if the link is healthy."""
        return self.healthy

    def get_state(self):
        """Returns a copy of the current state."""
        return copy.deepcopy(self.state)

    def send_heartbeat(self):
        """Sends a heartbeat to make sure the serial link stays ok."""
        if not acquire(self.write_lock, 5):
            # Another thread is holding the write lock. This is really weird.
            # Just give up and declare ourselves unhealthy.
            self.healthy = False
            return
        try:
            self.serial.write('H\n')
            self.last_heartbeat_time = time.time()
        finally:
            self.write_lock.release()


class Arduino(object):
    """Talks to an Arduino controller to read sensors and drive motors."""

    # Timeout for buffered serial I/O in seconds.
    IO_TIMEOUT_SEC = 5

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
        self.serial = serial.Serial(port=port,
                baudrate=baud_rate, bytesize=8, parity='N', stopbits=1,
                timeout=self.IO_TIMEOUT_SEC, writeTimeout=self.IO_TIMEOUT_SEC)
        if not self.serial.isOpen():
            raise ValueError("Couldn't open %s" % port)

        # How many commands the server has sent to the Arduino.
        self.commands_sent = 0

        # Used to share the serial port with the monitor.
        self.write_lock = threading.Lock()

        self.monitor = SerialMonitor(self.serial, self.write_lock)
        self.monitor.start()

    def is_healthy(self):
        """Returns True if our link with the Arduino is healthy."""
        return self.monitor.is_healthy()

    def get_commands_sent(self):
        """Returns how many commands we think we've sent."""
        return self.commands_sent

    def get_state(self):
        """Returns the current state of the Arduino."""
        return self.monitor.get_state()

    def stop(self):
        """Shuts down communication between the server and the Arduino."""
        self.monitor.stop()
        # Wait for the monitor to stop.
        self.monitor.join(timeout=5)
        # Maybe that worked, maybe it didn't. We're probably trying to reset
        # here, so just shut down hard and move on.
        if self.monitor.is_alive():
            logging.error('Monitor did not stop.')
        self.serial.close()

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
            self.serial.write(command + "\n")
            self.serial.flush()
            self.commands_sent += 1
        finally:
            self.write_lock.release()
        return True


def acquire(lock, timeout):
    """Acquire lock with a timeout"""
    if lock.acquire(False):
        return True

    start_time = time.time()
    while time.time() < start_time + timeout:
        if lock.acquire(False):
            return True
        time.sleep(.1)

    return False

if __name__ == '__main__':
    a = Arduino('/dev/ttyACM0')
    try:
        while True:
            time.sleep(1)
            print a.get_state()
    finally:
        a.stop()
