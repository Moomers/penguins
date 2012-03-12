#!/usr/bin/python

import commands
import os, os.path
import serial
import tempfile
import time
import traceback

from xml.etree import ElementTree

import common

class SMCSerialController(object):
    """Represents a single SMC accessible via a serial port"""
    def __init__(self, port, smccmd):
        """Initializes the serial port and establishes communication with the SMC there

        Will fail if the device at the port is not an SMC"""
        #make sure our port looks right
        self.port = port
        if not port.startswith('/dev/ttyACM'):
            raise ValueError("Invalid port '%s': should be '/dev/ttyACM<#>'" % port)
        if not os.path.exists(port):
            raise ValueError("No such port '%s'" % port)

        #get the serial number
        self.serial = get_serial_by_port(port)

        #make sure we're in ascii mode
        self.smccmd = smccmd
        self._ensure_ascii_mode()

        #some global vars
        self.reset_count = 0

        #open the serial connection
        self.dev = serial.Serial(port, timeout = 1)

        #clear the pipes
        self.dev.write('\n')
        self.dev.flush()
        if self.dev.inWaiting():
            self.dev.read(self.dev.inWaiting())

    def _ensure_ascii_mode(self):
        """Makes sure the controller is set into ascii mode using SmcCmd"""
        fd, temp_name = tempfile.mkstemp()
        try:
            conffile = os.fdopen(fd, 'r+')
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
                    conffile.flush()

                    command = "%s -d %s --configure %s" % (self.smccmd, self.serial, temp_name)
                    status, output = commands.getstatusoutput(command)
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
        if not command:
            raise ValueError("Invalid command '%s': it's blank!" % command)

        #send the command
        while True:
           try:
              self.dev.write(command)
              self.dev.write('\n')

              #get and parse the result
              result = self.dev.readline().strip()
              if not result:
                 raise common.ControllerError("result was empty")

           except common.ControllerError:
              print "*** Got an empty response, trying command %s again ***" % command

           except:
              print "*** Error on sending command '%s' ***" % command
              traceback.print_exc()

              time.sleep(.2)
              self.reset()
              self.reset_count += 1
           else:
              break

        status = result[0]
        if status == '?':
            raise ValueError("Command '%s' was not understood" % command)
        elif status not in ('.','!'):
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

    def _bit_query(self, bits, data):
        """Determines which of the bits in `bits` is set in `data`

        Bits should be a mapping from bit => bit name;
        Returns a mapping from bit name => True/False"""
        result = {}
        for bit, name in bits.items():
            val = 1 << bit
            result[name] = ((val & data) == val)

        return result

    ############# Public Interface #############
    @property
    def status(self):
        """Returns the status of the controller"""
        #start out with the product and firmware
        status = self._get_version()

        #are we having any errors atm?
        status['errors'] = self._bit_query(common.ControllerError.STATUS, self._get_variable(0))
        status['speed'] = self.speed
        status['reset_count'] = self.reset_count

        return status

    def reset(self):
        """Gets the controller ready to drive"""
        self.speed = 0
        status, output = self._send_command('GO')
        if status != 'running':
            raise common.ControllerError("Motor still stopped after reset; additional errors may be present")

    def stop(self):
        """Stops the motor on this controller"""
        #self._send_comand("X")
        self.brake(32)

    def brake(self, speed):
        """Slows down the motor with the specified acceleration"""
        self._send_command("B%d" % speed)

    def get_speed(self):
        """Returns current speed"""
        return self._get_variable(21)
    def set_speed(self, speed):
        """Sets the current speed"""
        cmd = 'R' if speed < 0 else 'F'
        self._send_command("%s%d" % (cmd, abs(speed)))

    speed = property(
            lambda self: self.get_speed(),
            lambda self, speed: self.set_speed(speed),
            )

def get_serial_by_port(port):
    """gets the serial number corresponding to the device on the port"""
    #get the controller's serial number out of sysfs
    devname = os.path.basename(port)
    try:
        return open('/sys/class/tty/%s/device/../serial' % devname).read().strip()
    except:
        raise ValueError("Cannot retrieve serial number for device '%s'" % devname)

def get_driver(left, right, smccmd, **rest):
    """Utility function which returns a driver using the controllers defined here"""
    controllers = {
            'left':{'serial':left_id, 'controller':None},
            'right':{'serial':right_id, 'controller':None},
            }

    #look through ttyACM devices to find one with a matching serial number
    files = os.listdir('/dev')
    for f in files:
        if not f.startswith('ttyACM'):
            continue

        port = os.path.join('/dev', f)
        try:
           serial = get_serial_by_port(port)
        except:
           continue

        for c in controllers.values():
            if c['serial'] == serial:
                c['controller'] = SMCSerialController(port, smccmd)

    #make sure we have controllers for both sides
    for side, c in controllers.items():
        if not c['controller']:
            raise common.DriverError("Cannot find controller with serial number %s (%s side)" % (c['serial'], side))
        else:
            print "Found %s controller on port %s" % (side, c['controller'].port)

    #return the driver using the two controllers we found
    return common.SmcDriver(controllers['left']['controller'], controllers['right']['controller'])
