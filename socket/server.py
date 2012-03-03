#!/usr/bin/python

import Queue
import SocketServer
import threading

import drivers

class Controller(object):
    """Turns client requests into driver commands"""
    def __init__(self, command_queue, driver):
        self.queue = command_queue
        self.driver = driver

    def controller(self):
        """The main function, meant to be in a thread, which drives the robot"""
        while True:
            command = self.queue.get()

            try:
                parts = command.split()
                if parts[0] == 'stop':
                    self.driver.stop()

                elif parts[0] == 'speed':
                    self.driver.speed = parts[1]
                elif parts[0] == 'brake':
                    self.driver.brake(parts[1])

                elif parts[0] == 'left':
                    self.driver.left = parts[1]
                elif parts[0] == 'right':
                    self.driver.right = parts[1]

            except Exception, e:
                print "error processing command %s: %s" % (command, str(e))


            self.queue.task_done()

class CommandReciever(SocketServer.StreamRequestHandler):
    def handle(self):
        """writes requests from the client into a queue"""
        while True:
            command = self.rfile.readline().strip()

            if command == "exit":
                self.wfile.write("done\n")
                break

            if command == "empty":
                discarded= []
                while not self.server.command_queue.empty():
                    item = self.server.command_queue.get_nowait()
                    discarded.append(item)
                    self.server.command_queue.task_done()
                self.wfile.write("ok, removed %s items\n" % len(discarded))
            else:
                self.server.command_queue.put(command)
                self.wfile.write("ok, %s commands in the queue\n" % self.server.command_queue.qsize())

if __name__ == "__main__":
    HOST, PORT = "localhost", 9999

    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), DriverHandler)
    server.command_queue = Queue.Queue()
    #server.driver = driver.SmcCmdDriver()

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
