#!/usr/bin/python

import time
from collections import deque

class Sensor(object):
    """This class defines an interface that all sensors must implement"""
    pass

class ArduinoConnectedSensor(Sensor):
    """A sensor connected to the on-board arduino on the robot"""
    def __init__(self, robot, key):
        Sensor.__init__(self)

        self.robot = robot
        self.key = key

    def _read(self):
        try:
            reading = self.robot.arduino.sensor_readings[self.key]
            return reading
        except KeyError:
            return None

class VoltageSensor(ArduinoConnectedSensor):
    """An analog sensor for determining voltage; uses a voltage divider on the arduino"""
    def __init__(self, robot, key, R1 = 1, R2 = 1):
        ArduinoConnectedSensor.__init__(self, robot, key)

        # resistors used on the divider, in ohms
        self.ratio = float(R1 + R2) / float(R2)

        self.readings = deque([0] * 20, 20)

    @property
    def voltage(self):
        """Voltage is actually an average of several readings"""
        return sum(self.readings)/len(self.readings)

    def read(self):
        """reads the raw millivolt value from the arduino and scales it by the voltage divider ratio"""
        reading = self._read()
        if reading is not None:
            voltage = self.ratio * float(reading.data) * 5 / 1023
            self.readings.popleft()
            self.readings.append(voltage)

        return self.voltage

    @property
    def status(self):
        return {'value':self.voltage, 'units':'mV'}

class TemperatureSensor(ArduinoConnectedSensor):
    """A TMP36 connected to the arduino"""
    def __init__(self, robot, key, scaling_function = lambda voltage: (voltage - 500) / 10):
        ArduinoConnectedSensor.__init__(self, robot, key)
        self.scaling_function = scaling_function

        self.readings = deque([0]*20, 20)

    @property
    def temperature(self):
        """Temperature is actually an average of the last X readings"""
        return sum(self.readings)/len(self.readings)

    def read(self):
        reading = self._read()
        if reading is not None:
            mV = float(reading.data) * (5.0 / 1023) * 1000
            temperature = self.scaling_function(mV)
            self.readings.popleft()
            self.readings.append(temperature)

        return self.temperature

    @property
    def status(self):
        return {'value':self.temperature, 'units':'C'}

class Sonar(ArduinoConnectedSensor):
    """An LV-MaxSonar -EZ1 connected to the Arduino (via PWM)"""
    def __init__(self, robot, key):
        ArduinoConnectedSensor.__init__(self, robot, key)

    def read(self):
        reading = self._read()
        if reading is None:
            self.distance = None
        else:
            self.distance = int(reading.data)

        return self.distance

    @property
    def status(self):
        return {'value':self.distance, 'units':'"'}

class Encoder(ArduinoConnectedSensor):
    """A magnetic encoder reading the wheel speed via a hall effect sensor"""
    def __init__(self, robot, key, magnets = 2, min_interval = 2):
        ArduinoConnectedSensor.__init__(self, robot, key)

        self.magnets = float(magnets)
        self.min_interval = min_interval

        self.readings = []

    @property
    def rpm(self):
        try:
            first, last = (self.readings[0], self.readings[-1])
        except:
            first, last = (None, None)

        if first is None or last is None or first == last:
            return 0

        interval = first.timestamp - last.timestamp
        pulses = int(first.data) - int(last.data)
        rpms = (float(pulses) / self.magnets) * (60.0 / interval)
        return rpms

    def read(self):
        """Process the RPMs of the encoder"""
        reading = self._read()

        # do we add this new reading to the list?
        # ignore null readings
        if reading is None:
            pass

        # always add if we have nothing else
        elif len(self.readings) == 0:
            self.readings.append(reading)

        # don't double-add
        elif reading.timestamp == self.readings[-1].timestamp:
            pass

        # finally, add remaining readings
        else:
            self.readings.append(reading)


        # now prune old readings
        now = time.time()
        pruned = [r for r in self.readings if (now - r.timestamp) < self.min_interval]
        self.readings = pruned

        return self.rpm

    @property
    def status(self):
        return {'value':self.rpm, 'units':'RPM'}

class SensorReading(object):
    """Represents a reading from a sensor attached to the arduino"""
    def __init__(self,
            timestamp = time.time(),
            sensor_name = '',
            data = None):
        self.timestamp = timestamp
        self.sensor_name = sensor_name
        self.data = data

    def __repr__(self):
        return "SensorReading(timestamp=%f, sensor_name=%s, data=%s)" % (
                self.timestamp,
                self.sensor_name,
                self.data)

