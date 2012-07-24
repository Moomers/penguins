
class Arduino(object):
    """Object representing an Arduino on-board a penguin"""
    def __init__(self, port):
        self.port = port

    def stop(self):
        """Shuts down communication between the server and the arduino"""
        pass

    def heartbeat(self):
        """Runs in a thread; sends a regular heartbeat to the arduino"""
        pass

    def send_command(self):
        pass


