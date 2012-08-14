#!/usr/bin/python

class DriverError(Exception):
   """Used when the driver encounters an error executing the command"""
   pass

class StoppedError(DriverError):
    """Signals that a command was invalid because we're in emergency stop mode"""
    pass

class ParameterError(DriverError):
    """Used when the driver cannot execute a command because it exceeds a parameter"""
    pass

class ControllerError(DriverError):
    """Used to indicate an error inside a controller"""
    pass
