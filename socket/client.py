import socket

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

        result = self.server.readline().split(',', 1)
        if result[0] == 'ok':
            return result[1].strip()
        else:
            raise Exception(result[1].strip())


    ###### the interface of the driver #####
    def brake(self, speed):
        return self._send_command("brake %s" % speed)

    def stop(self):
        return self._send_command("stop")

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
