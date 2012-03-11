#!/usr/bin/python

import SocketServer
import drivers, drivers.smcserial, drivers.smcstub
import sys
import traceback

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
                self.wfile.write("invalid, %s\n" % e.message)
                self.wfile.flush()
            except Exception, e:
                traceback.print_exc()
                self.wfile.write("error, command %s - %s\n" % (command, str(e)))
                self.wfile.flush()
            else:
                self.wfile.write("ok, %s\n" % output)
                self.wfile.flush()

if __name__ == "__main__":
    HOST, PORT = '', 9999
    left = '3000-6A06-3142-3732-7346-2543'
    right = '3000-6F06-3142-3732-4454-2543'
    smcpath = '/root/pololu/smc_linux/SmcCmd'

    if len(sys.argv) > 1 and sys.argv[1] == 'stub':
        driver = drivers.smcstub.get_driver(left, right)
    else:
        driver = drivers.smcserial.get_driver(left, right, smcpath)

    # Create the server, binding to localhost on port 9999
    server = TCPServer((HOST, PORT), DriverHandler)
    server.driver = driver

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    try:
        server.serve_forever()
    except KeyboardInterrupt, e:
        print 'Shutting down.'
        server.server_close()
