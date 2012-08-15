#!/usr/bin/python

import commands
import curses
import time
import threading

class CursesUI(threading.Thread):
    """A curses UI or talking to a driver via client"""
    def __init__(self):
        """Initializes ncurses"""
        threading.Thread.__init__(self, name='curses-ui')

        # used to stop the UI loop
        self._stop = threading.Event()

        # keep track of the last keystroke
        # it is cleared and returned by get_command
        self._last_key = None

    def init(self):
        """Sets up ncurses and creates all the windows"""
        #initialize ncurses
        self.stdscr = curses.initscr()
        self.windows = {'stdscr':self.stdscr}

        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)

        curses.curs_set(0)
        curses.halfdelay(1)

        #initialize the status and result windows
        self.windows['time'] = self.create_window(' Time ', 3, 82, 0, 0)

        self.windows['driver'] = self.create_window(' Driver Status ', 12, 40, 3, 0)
        self.windows['monitor'] = self.create_window(' Monitor Status ', 12, 40, 3, 41)
        self.windows['arduino'] = self.create_window(' Arduino Status ', 10, 40, 14, 0)
        self.windows['sensors'] = self.create_window(' Sensor Status ', 10, 40, 14, 41)
        self.windows['result'] = self.create_window(' Last Result ', 3, 82, 25, 0)

    def cleanup(self):
        """Clean up ncurses"""
        self.stdscr.keypad(0)
        curses.nocbreak()
        curses.echo()

        curses.endwin()

    def run(self):
        """The main loop"""
        while not self._stop.is_set():
            self.write_line(self.windows['time'], 1, "%.2f" % time.time(), align = 'center')
            for window in self.windows.values():
                window.refresh()

            try:
                self._last_key = self.stdscr.getkey()
            except:
                pass

    def stop(self):
        """Stops the UI loop"""
        self._stop.set()
        self.join()
        self.cleanup()

    def create_window(self, title, height, width, top, left, border = True):
        """Creates a window"""
        window = curses.newwin(height, width, top, left)

        if border:
            window.box()
        if title:
            self.write_line(window, 0, title, left_margin = 3, nopad = True)

        self.windows['stdscr'].refresh()
        return window

    def write_key_value(self, window, linenum, key, value):
        """Properly formats and writes a key-value pair"""
        key = str(key)
        value = str(value)

        max_width = window.getmaxyx()[1] - 2 #subtract 2 for borders
        key_len = max_width - len(value) - 1 #subtract 1 for the space between k and v

        line = "%s %s" % (key[:key_len].ljust(key_len), value)
        self.write_line(window, linenum, line)

    def write_line(self, window, linenum, line, align = 'left', left_margin = 1, right_margin = 1, nopad = False):
        """Writes a line in the specified window"""
        h, w = window.getmaxyx()
        if linenum > h:
            return

        #truncate the string to fit perfectly inside the window
        if not nopad:
            length = w - left_margin - right_margin
            # first trim too-long lines
            line = line[:w-2]

            # next justify the line
            align_fun = {
                    'left':line.ljust,
                    'right':line.rjust,
                    'center':line.center,
                    }
            line = align_fun[align](length)

        window.addstr(linenum, left_margin, line)

    def write_result(self, result):
        self.write_line(self.windows['result'], 1, str(result))

    def update_status(self, status):
        """puts the current status into the status windows"""
        for cat, s in status.items():
            if cat == 'sensors':
                continue

            window = self.windows[cat]
            linenum = 1
            for key, val in s.items():
                if key == 'alerts':
                    # print out monitor alerts
                    self.write_line(window, linenum, 'Alerts:')
                    linenum += 1
                    for k, v in val.items():
                        self.write_key_value(window, linenum, '  '+k, v)
                        linenum += 1
                else:
                    self.write_key_value(window, linenum, key, val)
                    linenum += 1

        sen_line = 1
        for sen in status['sensors']:
            val = "%s%s" % (sen['value'], sen['units'])
            self.write_key_value(self.windows['sensors'], sen_line, sen['name'], val)
            sen_line += 1

    def get_command(self):
        """Returns the user's last command"""
        try:
            if self._last_key == 'q':
                return commands.Quit()
            elif self._last_key == 'g':
                return commands.Go()
            elif self._last_key == 'r':
                return commands.Reset()
            elif self._last_key == 's':
                return commands.Stop()
            elif self._last_key == 't':
                return commands.Shutdown()
            elif self._last_key == 'b':
                return commands.Brake(1)
            elif self._last_key == 'h':
                return commands.Hold()
            elif self._last_key == 'KEY_LEFT':
                return commands.Steer(direction=-1)
            elif self._last_key == 'KEY_RIGHT':
                return commands.Steer(direction=1)
            elif self._last_key == 'KEY_DOWN':
                return commands.Drive(speed=-1)
            elif self._last_key == 'KEY_UP':
                return commands.Drive(speed=1)

            else:
                return None

        finally:
            self._last_key = None
        self.cleanup()

    def error_notify(self, error):
        """Displays the error in the results window"""
        self.write_result("Error at %.2f: %s" % (time.time(), str(error)))

def get_ui(**options):
    return CursesUI()

if __name__ == "__main__":
    ui = get_ui()
    ui.init()

    ui.start()
    try:
        while True:
            time.sleep(0.05)

            command = ui.get_command()
            if not command:
                continue
            if type(command) == commands.Quit:
                break
            else:
                ui.write_result("command was %s" % str(command))
    finally:
        ui.stop()


