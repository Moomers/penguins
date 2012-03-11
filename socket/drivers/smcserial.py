#!/usr/bin/python

import commands
import os, os.path
import serial
import tempfile
from xml.etree import ElementTree

import common

class SimpleMotorController(object):
    """Represents a single SMC accessible via a serial port"""
    def __init__(self, port, smccmd):
        """Initializes the serial port and establishes communication with the SMC there

        Will fail if the device at the port is not an SMC"""
        #make sure our port looks right
        if not port.startswith('/dev/ttyACM'):
            raise ValueError("Invalid port '%s': should be '/dev/ttyACM<#>'" % port)
        if not os.path.exists(port):
            raise ValueError("No such port '%s'" % port)

        #get the controller's serial number out of sysfs
        devname = os.path.basename(port)
        try:
            self.serial = open('/sys/class/tty/%s/device/../serial' % devname).read().strip()
        except:
            raise ValueError("Cannot retrieve serial number for device '%s'" % devname)

        #make sure we're in ascii mode
        self.smccmd = smccmd
        self._check_mode()

        #open the serial connection
        self.dev = serial.Serial(port, timeout = 1)

        #clear the pipes
        self.dev.write('\n')
        self.dev.flush()
        if self.dev.inWaiting():
            self.dev.read(self.inWaiting())

    def _check_mode(self):
        """Makes sure the controller is set into ascii mode using SmcCmd"""
        fd, temp_name = tempfile.mkstemp()
        try:
            conffile = os.fdopen(fd, 'rw')
        except:
            os.close(fd)
            raise
        else:
            try:
                #save the current config into the temp file
                status, output = commands.getstatusoutput("%s -d %s --getconf %s" % (self.smccmd, self.serial, temp_name))
                if status:
                    raise common.ControllerError("Cannot get current config for controller %s: %s" % (self.serial, output))

                #figure out the current mode
                conf = ElementTree.fromstring(conffile.read())
                mode = conf.find('SerialMode').text

                #set the mode to Ascii if needed
                if mode != 'Ascii':
                    conf.find('SerialMode').text = 'Ascii'
                    conffile.seek(0)
                    conffile.truncate()
                    conffile.write(ElementTree.tostring(conf))

                    status, output = commands.getstatusoutput("%s -d %s --configure %s" % (self.smccmd, self.serial, temp_name))
                    if status:
                        raise common.ControllerError("Cannot set serial mode to Ascii on controller %s: %s" % (self.serial, output))
            finally:
                conffile.close()
        finally:
            os.remove(temp_name)

    def _send_command(self, command):
        """Sends a command to the controller and returns the results"""
        #make sure we don't have any termination characters in the command
        command = command.strip()
        if '\r' in command or '\n' in command or chr(0) in command:
            raise ValueError("Invalid command '%s': commands cannot contain '\\r', '\\n' or NULL" % command)

        #send the command
        self.dev.write(command)
        self.dev.write('\n')
        self.dev.flush()

        #get and parse the result
        result = self.dev.readline()

        status = result[0]
        if status == '?':
            raise ValueError("Command '%s' was not understood" % command)
        elif status not in ('?','!'):
            raise common.ControllerError("Invalid output from controller: '%s'" % result)

        #return a tuple containing (status, output)
        output = result[1:] if len(result) > 1 else ''
        return ('running' if status == '.' else 'stopped', output.strip())

    def _get_variable(self, var_id):
        """returns integer value of the variable requested"""
        return int(self._send_command("D%d" % var_id)[1])

    def _get_version(self):
        """Get the device type and version info"""
        status, output = self._send_command('V')
        parts = output.split()
        return {'product':parts[0], 'firmware':parts[1]}

    def _reset(self):
        """Sets the motor speed to 0 and exits safe-start"""
        self.speed = 0
        status, output = self._send_command('GO')
        if status != 'running':
            raise common.ControllerError("Motor still stopped after reset; additional errors may be present")

    def _bitwise_query(self, bits, data):
        """Determines which of the bits in `bits` is set in `data`

        Bits should be a mapping from bit => bit name;
        Returns a mapping from bit name => True/False"""
        result = {}
        for bit, name in bits.items():
            val = 1 << bit
            result[name] = ((val & data) == val)

        return result

    @property
    def status(self):
        """Returns the status of the controller"""
        #start out with the product and firmware
        status = self._get_version()

        #are we having any errors atm?
        errors = {
                0:'safe start violation',
                1:'channel invalid',
                2:'serial error',
                3:'command timeout',
                4:'limit/kill switch',
                5:'low vin',
                6:'high vin',
                7:'over temperature',
                8:'motor driver error',
                9:'err line high'}

        status['errors'] = self._bitwise_query(errors, self._get_variable(0))
        return status
