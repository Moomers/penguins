#!/usr/bin/python

import curses
import time
import threading

class CursesUI(threading.Thread):
    """A curses UI or talking to a driver via client"""
    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def update_status(self, status):
        pass

    def get_command(self):
        pass

    def error_notify(self, error):
        pass

def get_ui(**options):
    return FramebufferUI()

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
            if command[0] == 'quit':
                break
            else:
                ui.error_notify("command was %s" % str(command))
    finally:
        ui.stop()


