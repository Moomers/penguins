#!/usr/bin/python

import SocketServer
import drivers, drivers.smcserial, drivers.smcstub, drivers.smccmd
import cPickle as pickle
import traceback

from optparse import OptionParser, OptionGroup

class CommandError(ValueError):
    pass

class TCPServer(SocketServer.TCPServer):
    # Bind to our port even if it's in TIME_WAIT, so we can restart the
    # server right away.
    allow_reuse_address = True

class DriverHandler(SocketServer.StreamRequestHandler):
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

    def handle(self):
        """writes requests from the client into a queue"""
        while True:
            command = self.rfile.readline().strip()
            if not command:
                self.wfile.write("\n")
                self.wfile.flush()
                continue

            if command == 'exit':
                self.wfile.write("done\n")
                self.wfile.flush()
                break

            try:
                driver = self.server.driver

                parts = command.split()
                if parts[0] == 'stop':
                    driver.stop()
                    output = 'robot stopped'

                elif parts[0] == 'brake':
                    try:
                        new_speed = self.parse_speed(parts)
                        if new_speed < 1 or new_speed > 100:
                            raise ValueError("out of range")
                    except:
                        raise CommandError("brake must be a number from 1 to 100")

                    driver.brake(new_speed)
                    output = 'braking initiated'

                elif parts[0] == 'status':
                    output = driver.status

                elif parts[0] in ('speed', 'left', 'right'):
                    #try to get a number out of parts[1]
                    try:
                        new_speed = self.parse_speed(parts)
                        if new_speed and (new_speed < -100 or new_speed > 100):
                            raise ValueError("out of range")
                    except Exception, e:
                        raise CommandError("speed must be a number from -100 to 100, %s" % e)

                    #figure out which if any motor we want to deal with
                    motor = parts[0] if parts[0] in ('left', 'right') else 'both'

                    if new_speed is not None:
                        driver.set_speed(new_speed, motor)
                        output = "speed set to %s" % new_speed
                    else:
                        speeds = driver.get_speed(motor)
                        output = ",".join([str(s) for s in speeds])

                else:
                    raise CommandError("invalid command '%s'" % command)

            except CommandError, e:
                self.send_output('invalid', e.message)
            except Exception, e:
                traceback.print_exc()
                self.send_output('error', str(e))
            else:
                self.send_output('ok', output)

def main():
    driverlist = {
            'smccmd':('Runs SmcCmd to process every request', drivers.smccmd),
            'smcserial':('Drives controllers using the serial protocol via a tty interface', drivers.smcserial),
            'smcstub':('Stub test driver for SMC controller-based drivers', drivers.smcstub),
            }

    parser = OptionParser()
    parser.add_option('-d', '--driver', action="store", type="choice", dest="driver", default="smcstub", choices=driverlist.keys(),
            help="Drive using this driver [Default: smcserial]")
    parser.add_option('-a', '--host', action="store", type="string", dest="host", default="",
            help="Host/address to listen on [Default: all (empty string)]")
    parser.add_option('-p', '--port', action="store", type="int", dest="port", default=9999,
            help="Port to listen on [Default: 9999]")

    parser.add_option('-v', "--verbose", action="store_true", dest="verbose", default=False,
            help="Print more debug info")

    parser.add_option("--list", action="store_true", dest="list", default=False,
            help="List the available drivers")

    smcgroup = OptionGroup(parser, "SMC-based driver options",
        "Needed when the driver is oriented around a pair of Pololu Simple Motor Controllers")
    smcgroup.add_option("-l", "--left", type="string", dest="left", default='3000-6A06-3142-3732-7346-2543',
            help="The serial number of the left controller [3000-6A06-3142-3732-7346-2543]")
    smcgroup.add_option("-r", "--right", type="string", dest="right", default="3000-6F06-3142-3732-4454-2543",
            help="The serial number of the right controller [3000-6F06-3142-3732-4454-2543]")
    smcgroup.add_option("-c", "--smccmd", type="string", dest="smccmd", default="/root/pololu/smc_linux/SmcCmd",
            help="The path to the SmcCmd utility [/root/pololu/smc_linux/SmcCmd]")
    parser.add_option_group(smcgroup)

    options, args = parser.parse_args()
    if options.list:
        for name, info in driverlist.items():
            print "%s %s" % (name.ljustify(30), info[0])

        return 0

    try:
        drivermod = driverlist[options.driver][1]
    except:
        parser.error("You must specify a driver")

    driver = drivermod.get_driver(**vars(options))
    server = TCPServer((options.host, options.port), DriverHandler)
    server.driver = driver

    try:
        server.server_forever()
    except:
        print "Shutting down"
        server.server_close()
    finally:
        driver.stop()

if __name__ == "__main__":
    main()
