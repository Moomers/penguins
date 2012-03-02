#!/usr/bin/python

import commands
import re

from common import DriverError

class SmcCmdDriver(object):
   """Drives motors using the SmcCmd program for pololu simple motor controllers"""
   speed_re = re.compile("^current speed:\s*(\d+)", re.IGNORECASE|re.MULTILINE)

   def __init__(self, left_motor_id, right_motor_id, smccmd_path):
      """pass the device ids"""
      self.motors = {
            'left':left_motor_id,
            'right':right_motor_id,
            }

      self.smccmd = smccmd_path

      #make sure the controller is ready to run
      self._set_speed(0)
      for motor in self.motors.keys():
         self._run_smc_command('--resume', motor)

   def _run_smc_command(self, command, motor):
      """Runs the specified command on the given motor"""
      final_command = [
         self.smccmd,
         "-d %s" % self.motors[motor],
         command,
         ]

      status, output = commands.getstatusoutput(" ".join(final_command))
      if status:
         raise DriverError(output)
      else:
         return output

   def _convert_speed(self, speed):
      """We want to specify speeds from 0 to 100, but the pololu uses 0 to 3200"""
      if speed > 100 or speed < -100:
         raise DriverError("Speed outside the normal range")

      return speed * 32

   def _convert_brake(self, brake):
      """We want a breaking value from 1 to 100, but the pololu uses 1 to 32"""
      if brake < 1 or brake > 100:
         raise DriverError("Braking speed outside the normal range")

      return 1 if brake < 3 else int((brake - 3)/3)

   def _set_speed(self, speed, motor = None):
      """sets the speed of one or both motors"""
      #easily handle setting both or a single motor
      motors = [motor] if motor else self.motors.keys()
      for motor in motors:
         self._run_smc_command("--speed %s" % self._convert_speed(speed), motor)

   def _get_speed(self, motor):
      """Returns the current speed of a motor"""
      output = self._run_smc_command('--status', motor)
      m = self.speed_re.search(output)
      if m:
         return int(m.group(1))
      else:
         raise DriverError("Cannot find motor speed; SmcCmd said: %s" % output)

   ###### the interface of the driver #####
   speed = property(
         lambda self: (self._get_speed('left'), self._get_speed('right')),
         lambda self, speed: self._set_speed(speed))

   left = property(
         lambda self: self._get_speed('left'),
         lambda self, speed: self._set_speed(speed, 'left'))
   right = property(
         lambda self: self._get_speed('right'),
         lambda self, speed: self._set_speed(speed, 'right'))

   def brake(self, speed):
      for motor in self.motors.keys():
         self._run_smc_command("--brake %s" % self._convert_brake(speed), motor)

   def stop(self):
      self.brake(100)
