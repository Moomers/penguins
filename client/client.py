#!/usr/bin/env python

import cPickle as pickle
import socket
import threading

from optparse import OptionParser, OptionGroup

import commands
import cursesui
import joyride
import framebuffer
import sound
import steering

class RobotCommandError(Exception):
    """Used when a robot command cannot be executed"""
    pass

class Robot(object):
    """Wraps the communication protocol with the robot server"""
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
            raise RobotCommandError(str(result))

    def disconnect(self):
        """Stops the motors and disconnects from the server"""
        self.stop()
        self._send_command('exit')
        self.sock.close()

    def become_controller(self):
        """Becomes the exclusive client driving the robot"""
        return self._send_command('control')

    def shutdown(self):
        """Tells the server to shut itself down."""
        self._send_command('shutdown')

    ###### the interface of the driver #####
    def brake(self, speed):
        """Gradually slows the robot at the specified speed"""
        return self._send_command("brake %s" % speed)

    def stop(self):
        """Stops the robot and prevents it from moving again"""
        return self._send_command("stop")

    def go(self):
        """Gets the robot ready to move"""
        return self._send_command('go')

    def reset(self):
        """Resets the robot into a known state"""
        return self._send_command('reset')

    def set_speed(self, speed, motor = 'both'):
        """sets the speed of one or both motors"""
        #easily handle setting both or a single motor
        motors = ['speed'] if motor == 'both' else [motor]
        outputs = []
        for motor in motors:
            output = self._send_command("%s %s" % (motor, speed))
            outputs.append(output.strip())

        return ", ".join(outputs)

    def get_status(self):
        return self._send_command('status')

class RobotClient(object):
    """Controls the robot"""
    def __init__(self, robot, ui, steering_model, sound):
        self.robot = robot
        self.ui = ui
        self.steering = steering_model
        self.sound = sound

        self._stop = threading.Event()

    def run(self):
        """Main loop which drives the robot"""
        while not self._stop.is_set():
            user_command = self.ui.get_command()
            if user_command:
                try:
                    if type(user_command) == commands.Quit:
                        self.robot.disconnect()
                        break
                    elif type(user_command) == commands.Shutdown:
                        self.robot.shutdown()
                        break
                    elif type(user_command) == commands.Horn and self.sound:
                        self.sound.play_honk()
                    elif type(user_command) == commands.Reset:
                        self.robot.reset()
                    elif type(user_command) == commands.Go:
                        self.robot.go()
                    elif type(user_command) == commands.Stop:
                        self.robot.stop()
                    elif type(user_command) == commands.Brake:
                        self.robot.brake(100)  # TODO what does this do?
                    elif type(user_command) in (
                            commands.Hold, commands.Drive, commands.Steer):
                        new_speeds = self.steering.parse_user_command(user_command)
                        self.robot.set_speed(int(new_speeds['left']), 'left')
                        self.robot.set_speed(int(new_speeds['right']), 'right')

                except RobotCommandError, e:
                    open('log', 'w+').write(str(e))
                    self.ui.error_notify(e)

            status = self.robot.get_status()
            self.ui.update_status(status)
            self.steering.update_status(status)

            if self.sound:
                self.sound.update_status(status)

def main():
    """If run directly, we will connect to a server and run the specified UI"""
    uilist = {
            'joyride':("Uses a joystick for steering and outputs console text", joyride),
            'curses':("A simple curses-based output UI with very basic arrow-key steering", cursesui),
            'framebuffer':("An output intenteded for the on-board computer, with no steering", framebuffer),
            }

    parser = OptionParser()

    uigroup = OptionGroup(parser, "UI options")
    uigroup.add_option('-u', '--ui', action="store", type="choice", dest="ui", default="joyride", choices=uilist.keys(),
            help="Interact with this type of UI [Default: joyride]")
    uigroup.add_option('-j', '--joystick', action="store", type="string", dest="joystick_device", default=None,
            help="Path to the device file of the joystick (for joyride UI) [Default: None]")
    uigroup.add_option('-s', '--disable-sound', action="store_false", dest="sound", default=True,
            help="Disable sound [Default: False]")
    uigroup.add_option("--list", action="store_true", dest="list", default=False,
            help="List the available UIs and exit")
    parser.add_option_group(uigroup)

    netgroup = OptionGroup(parser, "Network options")
    netgroup.add_option('-a', '--host', action="store", type="string", dest="host", default="localhost",
            help="Host/address to connect to [Default: localhost]")
    netgroup.add_option('-p', '--port', action="store", type="int", dest="port", default=9999,
            help="Port the server is listening on [Default: 9999]")
    parser.add_option_group(netgroup)

    options, args = parser.parse_args()

    list_and_exit = False
    if options.list:
        list_and_exit = True

    if not options.ui or options.ui not in uilist:
        print "You must pick one of the available UIs with --ui"

    if list_and_exit:
        print "Available UIs:"
        for name, info in uilist.items():
            print "%s %s" % (name.ljust(30), info[0])
        return 0

    # create the robot
    robot = Robot(options.host, options.port)
    status = robot.get_status()

    # create the ui
    uimod = uilist[options.ui][1]
    ui = uimod.get_ui(**vars(options))

    # create the steerer
    steerer = steering.SteeringModel(status)

    if options.sound:
        player = sound.SoundPlayer(status)
    else:
        player = None

    # create the robot client
    client = RobotClient(robot, ui, steerer, player)

    # start up all the pieces in the right order
    player.start()
    try:
        ui.init()
        ui.start()
        try:
            client.run()
        finally:
            ui.stop()
    finally:
        player.stop()

if __name__ == "__main__":
    main()
