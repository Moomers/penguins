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
                    try:
                        new_speed = parts[1]
                    except:
                        if parts[1] == 'speed':
                            speed = driver.speed
                            output = "%s, %s" % (speed[0], speed[1])
                        elif parts[1] == 'left':
                            output = driver.left
                        elif parts[1] == 'right':
                            output = driver.right
                    else:
                        try:
                            new_speed = int(parts[1])
                            if speed < -100 or speed > 100:
                                raise ValueError("out of range")
                        except:
                            raise CommandError("speed must be 'get' or a number from -100 to 100")
                        else:
                            if parts[1] == 'speed':
                                driver.speed = new_speed
                                output = "speed set to %s" % new_speed
                            elif parts[1] == 'left':
                                driver.left = new_speed
                                output = "left set to %s" % new_speed
                            elif parts[1] == 'right':
                                driver.right = new_speed
                                output = "right set to %s" % new_speed

            except CommandError, e:
                self.wfile.write("invalid, %s" % e.message)
            except Exception, e:
                self.wfile.write("error, command %s - %s" % (command, str(e)))
            else:
                self.wfile.write("ok, %s" % output)

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999

    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), DriverHandler)
    server.driver = drivers.SmcCmdDriver()

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
