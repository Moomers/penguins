import socket
import cPickle as pickle

from optparse import OptionParser, OptionGroup
import ui

HOST, PORT = "localhost", 9999
class DriverClient(object):
    def __init__(self, host, port):
        """connects to the driver server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

        self.server = self.sock.makefile('w')

    def _send_command(self, command):
        """Sends a command to the server"""
        command = "%s\n" % (command.strip())
        self.server.write(command)
        self.server.flush()

        #read the length of the result
        length = int(self.server.readline())
        output = self.server.read(length)

        result = pickle.loads(output)
        if result[0] == 'ok':
            return result[1]
        else:
            raise Exception(str(result))

    def disconnect(self):
        """Stops the motors and disconnects from the server"""
        self.stop()
        self.sock.close()

    ###### the interface of the driver #####
    def brake(self, speed):
        return self._send_command("brake %s" % speed)

    def stop(self):
        return self._send_command("stop")

    @property
    def status(self):
        return self._send_command('status')

    def set_speed(self, speed, motor = 'both'):
        """sets the speed of one or both motors"""
        #easily handle setting both or a single motor
        motors = ['speed'] if motor == 'both' else [motor]
        outputs = []
        for motor in motors:
            output = self._send_command("%s %s" % (motor, speed))
            outputs.append(output.strip())

        return ", ".join(outputs)

    def get_speed(self, motor = 'both'):
        """Returns the current speed of a motor"""
        if motor == 'both':
            speeds = self._send_command('speed')
            return [int(s.strip()) for s in speeds.split(',')]
        else:
            speed = self._send_command(motor)
            return [int(speed.strip())]

    speed = property(
            lambda self: self.get_speed('both'),
            lambda self, speed: self.set_speed(speed, 'both'))

    left = property(
            lambda self: self.get_speed('left')[0],
            lambda self, speed: self.set_speed(speed, 'left'))
    right = property(
            lambda self: self.get_speed('right')[0],
            lambda self, speed: self.set_speed(speed, 'right'))

def main():
    """If run directly, we will connect to a server and run the specified UI"""
    uilist = {
            'curses':("NCurses-based UI using arrow keys for steering", ui.CursesUI),
            }

    parser = OptionParser()
    parser.add_option('-i', '--ui', action="store", type="choice", dest="ui", default="curses", choices=uilist.keys(),
            help="Start up this UI [Default: curses]")
    parser.add_option('-v', "--verbose", action="store_true", dest="verbose", default=False,
            help="Print more debug info")
    parser.add_option("--list", action="store_true", dest="list", default=False,
            help="List the available UIs")

    netgroup = OptionGroup(parser, "Network options")
    netgroup.add_option('-a', '--host', action="store", type="string", dest="host", default="localhost",
            help="Host/address to connect to [Default: localhost]")
    netgroup.add_option('-p', '--port', action="store", type="int", dest="port", default=9999,
            help="Port the server is listening on [Default: 9999]")
    parser.add_option_group(netgroup)


    options, args = parser.parse_args()
    if options.list:
        for name, info in uilist.items():
            print "%s %s" % (name.ljustify(30), info[0])
        return 0

    client = DriverClient(options.host, options.port)
    try:
        try:
            interface = uilist[options.ui][1](client)
        except:
            parser.error("Cannot create UI '%s'" % options.ui)
        else:
            try:
                interface.run()
            finally:
                interface.cleanup()
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
