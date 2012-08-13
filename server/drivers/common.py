#!/usr/bin/python

class DriverError(Exception):
   """Used when the driver encounters an error executing the command"""
   pass

class ControllerError(DriverError):
    """Used to indicate an error inside a controller"""
    pass
