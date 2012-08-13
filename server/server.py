#!/usr/bin/python

import SocketServer
import cPickle as pickle
from contextlib import contextmanager
import sys
import time
import threading
import traceback

from optparse import OptionParser, OptionGroup

import arduino
import drivers
import monitor
import sensors

class CommandError(ValueError):
    pass

class TCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    # Bind to our port even if it's in TIME_WAIT, so we can restart the
    # server right away.
    allow_reuse_address = True

class ConnectionHandler(SocketServer.StreamRequestHandler):
    def parse_speed(self, parts):
        "parses the speed that comes over the wire into an int or None"
        try:
            new_speed = parts[1]
        except:
            return None
        else:
            return int(new_speed)

    def send_output(self, result, output):
        """Sends the output of the request to the client"""
        data = pickle.dumps((result, output))
        self.wfile.write('%d\n' % len(data))
        self.wfile.write(data)
        self.wfile.flush()

    def process_command(self, command):
        """Processes a command from the client and returns the correct output"""
        robot = self.server.robot

        parts = command.split()

        if parts[0] == 'stop':
            robot.stop()
            output = 'robot stopped'

        elif parts[0] == 'brake':
            try:
                new_speed = self.parse_speed(parts)
                if new_speed < 1 or new_speed > 100:
                    raise ValueError("out of range")
            except:
                raise CommandError("brake must be a number from 1 to 100")

            robot.brake(new_speed)
            output = 'braking initiated'

        elif parts[0] == 'status':
            output = robot.status

        elif parts[0] == 'reset':
            robot.reset()
            output = "robot reset successful"

        elif parts[0] == 'go':
            robot.go()
            output = "robot ready to run"

        elif parts[0] in ('speed', 'left', 'right'):
            #try to get a number out of parts[1]
            try:
                new_speed = self.parse_speed(parts)
                if new_speed is None or new_speed < -100 or new_speed > 100:
                    raise ValueError("out of range")
            except Exception, e:
                raise CommandError("speed must be a number from -100 to 100, %s" % e)

            #figure out which motor(s) we want to deal with
            motor = parts[0] if parts[0] in ('left', 'right') else 'both'
            robot.set_speed(new_speed, motor)

            printable_motor = "%s motor" if motor in ('left', 'right') else "both motors"
            output = "speed on %s set to %s" % (printable_motor, new_speed)

        else:
            raise CommandError("invalid command '%s'" % command)

        return output

    def handle(self):
        """handles a single client connection"""
        print "Client %s:%s connected" % self.client_address
        self.controller = False

        try:
            while not self.server.is_shutting_down.is_set():
                command = self.rfile.readline().strip()

                # meta commands: these control the meta operations
                # they do not drive the robot
                if not command:
                    self.send_output('ok', '')
                    continue

                if command == 'exit':
                    self.send_output('ok', 'done')
                    break

                if command == 'shutdown':
                    self.server.robot.shutdown()
                    break

                if command == 'control':
                    if self.controller:
                        self.send_output('ok', 'was already a controller')
                    else:
                        self.controller = self.server.robot.control_lock.acquire()
                        if self.controller:
                            self.send_output('ok', 'acquired control lock')
                        else:
                            self.send_output('error', 'cannot acquire control lock')

                    continue

                try:
                    output = self.process_command(command)
                except CommandError, e:
                    self.send_output('invalid', e.message)
                except Exception, e:
                    traceback.print_exc()
                    self.send_output('error', str(e))
                else:
                    self.send_output('ok', output)
                    self.server.last_request = time.time()

        finally:
            output = ["%s:%s disconnected" % self.client_address]
            if self.controller:
                self.server.robot.control_lock.release()
                self.server.robot.stop()
                output.append("; robot stopped. no more controlling client")
            else:
                output.append("; was a viewer")

            print "".join(output)

class Robot(object):
    """Represents the robot this server is controlling"""
    def __init__(self, driver, arduino_serial = None, **options):
        self.arduino_serial = arduino_serial

        # a real arduino is found during reset()
        self.arduino = None

        # initialize the driver
        drivermod = drivers.driverlist[driver][1]
        self.driver = drivermod.get_driver(robot = self, **options)

        # make a list of sensors
        self.sensors = {
                'Battery voltage':sensors.VoltageSensor(self, 'BV', 100000, 10000),
                'Driver temperature':sensors.TemperatureSensor(self, 'DT'),
                'Left sonar':sensors.Sonar(self, 'LS'),
                'Right sonar':sensors.Sonar(self, 'RS'),
                'Left encoder':sensors.Encoder(self, 'LE'),
                'Right encoder':sensors.Encoder(self, 'RE'),
                }

        # used to limit control of the robot to a single controlling thread
        self.control_lock = threading.RLock()
        # keep track of when the last command was issued to the robot
        self.last_control = 0

    def shutdown(self):
        """Stop accepting new requests, talking to the arduino, or moving"""
        self.driver.stop()
        self.arduino.stop()

    @property
    def status(self):
        """Return the status of the robot"""
        status = {
                'driver':self.driver.status,
                'arduino':self.arduino.status,
                'monitor':self.monitor.status,
                'sensors':[]}

        for name, sensor in self.sensors.items():
            sensor_status = sensor.status
            sensor_status['name'] = name
            status['sensors'].append(sensor_status)

        return status

    def reset(self):
        """Reset all of the components to a known initialized state"""
        with self._lock():
            if self.arduino:
                self.arduino.stop()

            self.arduino = arduino.find_arduino(self.arduino_serial)
            self.arduino.start_monitor()

            self.driver.stop()

    def go(self):
        """Puts the robot in go mode"""
        with self._lock():
            self.driver.go()

    def stop(self):
        """Stops the robot"""
        with self._lock():
            self.driver.stop()

    def brake(self, speed):
        """initiates braking"""
        with self._lock():
            self.driver.brake(speed)

    def set_speed(self, speed, motor):
        """sets the speed on one or both motors"""
        with self._lock():
            self.driver.set_speed(speed, motor)

    @contextmanager
    def _lock(self):
        """Utility function to protect control operations"""
        locked = self.control_lock.acquire(blocking = 0)
        if locked:
            try:
                yield
            finally:
                self.last_control = time.time()
                self.control_lock.release()
        else:
            raise Exception("Another thread is currently controlling the robot")


def main():
    """Parses command-line options and starts the robot-controlling server"""
    parser = OptionParser()
    parser.add_option('-v', "--verbose", action="store_true", dest="verbose", default=False,
            help="Print more debug info")
    parser.add_option("--list", action="store_true", dest="list", default=False,
            help="List the available drivers")

    opgroup = OptionGroup(parser, "Operational options")
    opgroup.add_option('-d', '--driver', action="store", type="choice", dest="driver", default="sabertooth", choices=drivers.driverlist.keys(),
            help="Drive using this driver [Default: sabertooth]")
    opgroup.add_option('-s', '--arduino', action="store", type="string", dest="arduino_serial", default=None,
            help="Serial number of the on-board arduino [Default: Pick a random one]")
    parser.add_option_group(opgroup)

    netgroup = OptionGroup(parser, "Network options")
    netgroup.add_option('-a', '--host', action="store", type="string", dest="host", default="",
            help="Host/address to listen on [Default: all (empty string)]")
    netgroup.add_option('-p', '--port', action="store", type="int", dest="port", default=9999,
            help="Port to listen on [Default: 9999]")
    parser.add_option_group(netgroup)

    smcgroup = OptionGroup(parser, "SMC-based driver options",
        "Needed when the driver is oriented around a pair of Pololu Simple Motor Controllers")
    smcgroup.add_option("-l", "--left", type="string", dest="left", default='3000-6A06-3142-3732-7346-2543',
            help="The serial number of the left controller [3000-6A06-3142-3732-7346-2543]")
    smcgroup.add_option("-r", "--right", type="string", dest="right", default="3000-6F06-3142-3732-4454-2543",
            help="The serial number of the right controller [3000-6F06-3142-3732-4454-2543]")
    smcgroup.add_option("-c", "--smccmd", type="string", dest="smccmd", default="/root/pololu/smc_linux/SmcCmd",
            help="The path to the SmcCmd utility [/root/pololu/smc_linux/SmcCmd]")
    parser.add_option_group(smcgroup)

    # parse the arguments
    options, args = parser.parse_args()

    list_and_exit = False
    if options.list:
        list_and_exit = True
    else:
        # make sure we specified a valid driver
        if not options.driver:
            print "You must specify a driver!"
            list_and_exit = True
        elif options.driver not in drivers.driverlist:
            print "Invalid driver specified: %s" % options.driver
            list_and_exit = True

    # if we requested a driver list, list drivers and then exit
    if list_and_exit:
        print "Available drivers:"
        for name, info in drivers.driverlist.items():
            print "%s %s" % (name.ljust(30), info[0])

        return 0

    # otherwise, try to create the robot and then start the servers
    robot = Robot(**vars(options))
    robot.reset()
    print "Robot initialized successfully..."

    # create the robot
    server = TCPServer((options.host, options.port), ConnectionHandler)
    server.last_request = 0
    server.robot = robot
    server.is_shutting_down = threading.Event()

    # create the monitor
    server_monitor = monitor.ServerMonitor(server, robot)
    server_monitor.start()

    # start the robot and begin accepting requests
    print "Starting server..."
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        print "Shutting down..."
        server.is_shutting_down.set()
        server_monitor.stop()
        server.shutdown()
        robot.shutdown()


if __name__ == "__main__":
    sys.exit(main())
