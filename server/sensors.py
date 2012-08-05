#!/usr/bin/python

import time

class Sensor(object):
    """This class defines an interface that all sensors must implement"""
    pass

class ArduinoConnectedSensor(Sensor):
    """A sensor connected to the on-board arduino"""
    def __init__(self, arduino, key):
        Sensor.__init__(self)

        self.arduino = arduino
        self.key = key

    def _read(self):
        try:
            return self.arduino.sensor_readings[self.key]
        except KeyError:
            return None

class VoltageSensor(ArduinoConnectedSensor):
    """An analog sensor for determining voltage; uses a voltage divider on the arduino"""
    def __init__(self, arduino, key, R1 = 1, R2 = 1):
        ArduinoConnectedSensor.__init__(self, arduino, key)

        self.voltage = None

        # resistors used on the divider, in ohms
        self.ratio = R2 / R1

    def read(self):
        """reads the raw millivolt value from the arduino and scales it by the voltage divider ratio"""
        reading = self._read()
        if reading is None:
            self.voltage = None
        else:
            self.voltage = self.ratio * reading.data

        return self.voltage

    @property
    def status(self):
        return {'value':self.voltage, 'units':'mV'}

class TemperatureSensor(ArduinoConnectedSensor):
    """A TMP36 connected to the arduino"""
    def __init__(self, arduino, key, scaling_function = lambda voltage: (voltage - 500) / 10):
        ArduinoConnectedSensor.__init__(self, arduino, key)
        self.scaling_function = scaling_function

    def read(self):
        reading = self._read()
        if reading is None:
            self.temperature = None
        else:
            self.temperature = self.scaling_function(reading.data)

        return self.temperature

    @property
    def status(self):
        return {'value':self.temperature, 'units':'C'}

class Sonar(ArduinoConnectedSensor):
    """An LV-MaxSonar -EZ1 connected to the Arduino (via PWM)"""
    def __init__(self, arduino, key):
        ArduinoConnectedSensor.__init__(self, arduino, key)

    def read(self):
        reading = self._read()
        if reading is None:
            self.distance = None
        else:
            self.distance = reading.data

        return self.distance

    def status(self):
        return {'value':self.distance, 'units':'"'}

class Encoder(ArduinoConnectedSensor):
    """A magnetic encoder reading the wheel speed via a hall effect sensor"""
    def __init__(self, arduino, key, magnets = 2, window = 5):
        ArduinoConnectedSensor.__init__(self, arduino, key)

        self.magnets = magnets
        self.readings = []

    def read(self):
        """Process the RPMs of the encoder"""
        # try adding a new reading from the sensor to the list of readings
        reading = self._read()
        if reading is not None and reading.timestamp > self.readings[-1].timestamp:
            self.readings.append(reading)

        # get rid of stale readins that don't fit into the current window
        now = time.time()
        for i in xrange(len(self.readings)):
            if self.readings[i].timestamp > (now - self.window):
                break
        self.readings = self.readings[i:]

        # count the number of pulses in the current window; pulse count is monotonically increasing
        pulses = self.readings[-1].data - self.readings[0].data
        time_period = self.readings[-1].timestamp - now

        self.rpm = pulses / self.magnets / (time_period / 60)
        return self.rpm

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
        return "SensorReading(timestamp=%f, sensor_name=%s, data=%s" % (
                self.timestamp,
                self.sensor_name,
                self.data)

