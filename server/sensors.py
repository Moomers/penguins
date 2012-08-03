#!/usr/bin/python

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

