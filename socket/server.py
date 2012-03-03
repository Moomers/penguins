#!/usr/bin/python

import SocketServer
import drivers

class CommandError(ValueError):
    pass

class DriverHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        """writes requests from the client into a queue"""
        while True:
            command = self.rfile.readline().strip()
            if not command:
                self.wfile.write("\n")
                continue

            if command == 'exit':
                self.wfile.write("done\n")
                break

            try:
                driver = self.server.driver

                parts = command.split()
                if parts[0] == 'stop':
                    driver.stop()
                    output = 'robot stopped'

                elif parts[0] == 'brake':
                    driver.brake(parts[1])
                    output = 'braking initiated'

                if parts[0] in ('speed', 'left', 'right'):
                    #try to get a number out of parts[1]
                    try:
                        new_speed = parts[1]
                    except:
                        new_speed = None
                    else:
                        try:
                            new_speed = int(new_speed)
                            if new_speed < -100 or new_speed > 100:
                                raise ValueError("out of range")
                        except:
                            raise CommandError("speed must be 'get' or a number from -100 to 100")

                    #figure out which if any motor we want to deal with
                    motor = parts[0] if parts[0] in ('left', 'right') else None

                    if new_speed:
                        driver.set_speed(new_speed, motor)
                        output = "speed set to %s" % new_speed
                    else:
                        speeds = driver.get_speed(motor)
                        output = ",".join(speeds)

            except CommandError, e:
                self.wfile.write("invalid, %s\n" % e.message)
            except Exception, e:
                self.wfile.write("error, command %s - %s\n" % (command, str(e)))
            else:
                self.wfile.write("ok, %s\n" % output)

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999

    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), DriverHandler)
    server.driver = drivers.SmcCmdDriver()

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
