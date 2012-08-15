#!/usr/bin/python

import logging
import os
import serial
import time
import threading

from parameters import monitor as mp

def touch(fname, times = None):
    fhandle = file(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close()

class SafetyChecker(object):
    def __init__(self):
        self.driver_overtemp_estop = False
        self.driver_overtemp_warn = False
        self.battery_estop = False
        self.battery_warn = False
        self.sonar_warn = False
        self.encoder_warn = False

    @property
    def status(self):
        status = {
                'Driver overtemp estop': self.driver_overtemp_estop,
                'Driver overtemp warn': self.driver_overtemp_warn,
                'Battery estop': self.battery_estop,
                'Battery warn': self.battery_warn,
                'Sonar warn': self.sonar_warn,
                'Encoder warn': self.encoder_warn
                }
        return status

    def should_estop(self):
        return self.driver_overtemp_estop or self.battery_estop

    def check(self, sensors):
        self.check_driver_temperature(sensors['Driver temperature'].temperature)
        self.check_battery_voltage(sensors['Battery voltage'].voltage)
        self.check_sonar(sensors['Left sonar'].distance, sensors['Right sonar'].distance)
        self.check_encoders(sensors['Left encoder'].rpm, sensors['Right encoder'].rpm)

    def check_driver_temperature(self, temp):
        """Warn if driver temperature too high; estop if critical."""
        if not self.driver_overtemp_estop and temp >= mp['driver_estop_temperature']:
            logging.warn('driver above critical temperature; estop')
            self.driver_overtemp_estop = True
        elif self.driver_overtemp_estop and temp <= mp['driver_safe_temperature']:
            logging.info('driver at safe temperature, clearing estop')
            self.driver_overtemp_estop = False

        if not self.driver_overtemp_warn and temp >= mp['driver_warn_temperature']:
            logging.warn('driver is getting too hot; warning')
            self.driver_overtemp_warn = True
        elif self.driver_overtemp_warn and temp <= mp['driver_safe_temperature']:
            logging.warn('driver at safe temperature, clearing warning')
            self.driver_overtemp_warn = False

    def check_battery_voltage(self, voltage):
        """Warn if battery voltage too low; estop if critical."""
        if not self.battery_estop and voltage <= mp['battery_estop_voltage']:
            logging.warn('battery below critical voltage; estop')
            self.battery_estop = True
        elif self.battery_estop and voltage >= mp['battery_safe_voltage']:
            logging.info('battery at safe voltage, clearing estop')
            self.battery_estop = False

        if not self.battery_warn and voltage <= mp['battery_warn_voltage']:
            logging.warn('battery undervoltage; warning')
            self.battery_warn = True
        elif self.battery_warn and voltage >= mp['battery_safe_voltage']:
            logging.warn('battery at safe voltage, clearing warning')
            self.battery_warn = False

    def check_sonar(self, left_dist, right_dist):
        """Warn if something is too close to either sonar."""
        min_dist = min(left_dist, right_dist)
        max_dist = max(left_dist, right_dist)
        if not self.sonar_warn and max_dist <= mp['sonar_warn_distance']:
            self.sonar_warn = True
        elif self.sonar_warn and min_dist >= mp['sonar_safe_distance']:
            self.sonar_warn = False

    def check_encoders(self, left_rpm, right_rpm):
        """Warn if wheel encoders show very different values."""
        diff = abs(right_rpm - left_rpm)
        if not self.encoder_warn and diff >= mp['encoder_warn_delta']:
            self.encoder_warn = True
        elif self.encoder_warn and diff <= mp['encoder_safe_delta']:
            self.encoder_warn = False

class ServerMonitor(threading.Thread):
    """Monitors the server and robot and takes action on exceptional conditions"""
    def __init__(self, server, robot):
        threading.Thread.__init__(self)
        self.server = server
        self.robot = robot

        # used to reduce log verbosity by only alerting once
        # for each type of problem
        self.log_estop = True
        self.log_slowdown = True
        self.log_control_estop = True
        self.log_arduino_unhealthy = True
        self.log_failed_reset = True

        self.last_reset_attempt = 0
        self.last_touched = 0

        self.safety_checker = SafetyChecker()

        # used to stop the monitor thread
        self._stop = threading.Event()

    def run(self):
        """Polls for state and sends a heartbeat."""
        # Run until told to stop.
        while not self._stop.isSet():
            try:
                for sensor in self.robot.sensors.values():
                    sensor.read()

                self.safety_checker.update(self.robot.sensors)
                if self.safety_checker.should_estop():
                    self.robot.driver.stop()

                if not self.robot.arduino.is_healthy():
                    if self.log_arduino_unhealthy:
                        logging.warn('arduino became unhealthy!')
                        self.log_arduino_unhealthy = False

                    if time.time() - self.last_reset_attempt > mp['time_between_reset_attempts']:
                        try:
                            self.robot.reset()
                        except:
                            if self.log_failed_reset:
                                logging.exception("failed to reset arduino")
                                self.log_failed_reset = False
                else:
                    self.log_failed_reset = True
                    if not self.log_arduino_unhealthy:
                        self.log_arduino_unhealthy = True
                        logging.info("arduino becomes healthy again!")

                # brake if the client hasn't said anything for a while
                if self.client_age() > mp['client_timeout']:
                    # print out this log message once per timeout
                    if self.log_estop:
                        logging.error('monitor estop; client_age %.4f' % (
                            self.client_age(),))
                    self.robot.driver.stop()
                    self.log_estop = False
                else:
                    self.log_estop = True

                # slow down if client hasn't issued control commands for a while
                if self.control_age() > mp['control_timeout_brake'] and not (
                        self.robot.driver.braking_speed or self.robot.arduino.status['estop']):
                    if self.log_slowdown:
                        logging.warn('braking; control_age %.4f' % (
                                self.control_age(),))

                    self.robot.driver.brake(mp['timeout_brake_speed'])
                    self.log_slowdown = False
                # emergency brake if still no control.
                elif self.control_age() > mp['control_timeout_stop'] and not self.robot.arduino.status['estop']:
                    if self.log_control_estop:
                        logging.warn('controlled estop; control_age %.4f' % (
                            self.control_age(),))
                    self.log_control_estop = False
                    self.robot.driver.stop()
                else:
                    self.log_slowdown = True
                    self.log_control_estop = True

                # touch a file every so often to tell watchdog we're still here
                if time.time() - self.last_touched > mp['file_touch_interval']:
                    touch(mp['file_touch_path'])
                    self.last_touched = time.time()

                # send new robot speed
                self.robot.driver.update_speed()

                time.sleep(mp['loop_min_interval'])

            except serial.SerialException:
                if self.robot.arduino.is_healthy():
                    logging.exception("Unexpected serial error while arduino is healthy")
            except:
                logging.exception("Unexpected error in monitor loop")

    def stop(self):
        """Signals that the monitor thread should stop."""
        self._stop.set()

    def client_age(self):
        """Time since last client request to the robot's server"""
        return round(time.time() - self.server.last_request, 2)

    def control_age(self):
        """Time since last control command to the robot"""
        return round(time.time() - self.robot.last_control, 2)

    @property
    def status(self):
        """Returns the monitor status"""
        status = {
                'client_age':self.client_age(),
                'control_age':self.control_age(),
                'alerts':self.safety_checker.status
                }

        return status


