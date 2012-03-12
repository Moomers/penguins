#!/usr/bin/python

import client
import curses
import sys
import time

class CursesUI(object):
    """A curses UI or talking to a driver via client"""
    def __init__(self, host, port):
        """Initializes ncurses and the client interface"""
        #initialize the client
        self.client = client.DriverClient(host, port)

        #initialize ncurses
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(1)

        curses.curs_set(0)
        curses.halfdelay(5)

        #lets do everything else in a try so we can clean up
        try:
            #initialize the windows
            self.windows = {'stdscr':self.stdscr}

            left = curses.newwin(30, 80, 0, 0)
            left.box()
            self.add_title(left, " Left Motor Status ")
            self.windows['left'] = left

            right = curses.newwin(30, 100, 0, 80)
            right.box()
            self.add_title(right, " Right Motor Status ")
            self.windows['right'] = right

            result = curses.newwin(3, 200, 31, 0)
            result.box()
            self.add_title(result, " Last Result ")
            self.windows['result'] = result

        except:
            self.cleanup()
            raise

    def cleanup(self):
        """Clean up ncurses"""
        self.stdscr.keypad(0)
        curses.nocbreak()
        curses.echo()

        curses.endwin()

    def write_line(self, window, linenum, line, align = 'left', left_margin = 1, right_margin = 1, nopad = False):
        """Writes a line in the specified window"""
        h, w = window.getmaxyx()
        if linenum > h:
            return

        #truncate the string to fit perfectly inside the window
        if not nopad:
            length = w - left_margin - right_margin
            align_fun = {
                    'left':line.ljust,
                    'right':line.rjust,
                    'center':line.center,
                    }
            line = align_fun[align](length)

        window.addstr(linenum, left_margin, line)

    def add_title(self, window, title):
        self.write_line(window, 0, title, left_margin = 3, nopad = True)

    def write_result(self, result):
        self.write_line(self.windows['result'], 1, result)

    def update_status(self):
        pass

    def run(self):
        """The main loop"""
        while True:
            for window in self.windows.values():
                window.refresh()

            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == -1:
                self.write_result("no key pressed")
            elif c == ord('p'):
                self.write_result('Bob was here at %s' % time.time())
            else:
                self.write_result('we got something odd: "%d"' % c)

if __name__ == "__main__":
    ui = CursesUI('localhost', 9999)
    try:
        ui.run()
    finally:
        ui.cleanup()
