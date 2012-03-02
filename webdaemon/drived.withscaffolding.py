#!/usr/bin/python

# dom0 vm management daemon
# last modified: $Date$
# last author:   $Author$

import commands
import os, os.path, shutil, tempfile
import signal
import sys
import time

import urllib, urllib2

import json

import logging, logging.handlers

#set a null logger for this library
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logging.getLogger('drived').addHandler(NullHandler())

def setupLogging():
	logger = logging.getLogger('drived')
	logger.setLevel(logging.INFO)	 #main severity level

	logger.debug("Adding file handler")

	#the default file handler for most messages
	fh = logging.handlers.RotatingFileHandler('/var/log/drived.log', maxBytes = 1000000)
	fh.setLevel(logging.DEBUG)
	fformatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s -- %(message)s (%(threadName)s %(module)s:%(lineno)d)")
	fh.setFormatter(fformatter)
	logger.addHandler(fh)

	return logger

import cherrypy
class Root(object):
	@cherrypy.expose
	def default(self, *pos, **others):
		return "Welcome to the drived management daemon: %s %s" % (pos, others)

class WebInterface(object):
	"""Provides a web interface to the VM manager using CherryPy"""
	def __init__(self):
		"""Initializes the web interface for the VM manager"""
		self.logger = logging.getLogger("drived.interface")
		self.logger.setLevel(logging.INFO)

		self.configureTools()

	def configureTools(self):
		"""Configures the tools this application uses and sets them to on in the config"""
		def formatter(next_handler, *args, **kwargs):
			"""Format the results from the function calls"""
			cherrypy.response.headers['Content-type'] = 'application/json'
			try:
				output = next_handler(*args, **kwargs)
			except Exception, e:
				logger = logging.getLogger('drived.interface')
				logger.exception("Error in UI:")

				return json.write({'result':'error', 'message':str(e)})
			else:
				try:
					return json.write(output)
				except:	#fall back on regular return if cannot encode to json
					return output
		cherrypy.tools.formatter = cherrypy._cptools.HandlerWrapperTool(formatter)

		self._cp_config = {
				'tools.formatter.on':True,
				}

	@cherrypy.expose
	def default(self, *pos, **form):
		"""The exposed method which handles all urls used allowed functions"""
		self.logger.debug("handling unknown request")
		return json.write({'result':'error', 'message':'unknown request'})

	#**************** STUFF FOR LOCAL SYSTEM MANIPULATION **************#
	@cherrypy.expose
	def updateLocalFile(self, filename, data = None, permissions = None):
		"""Update a local file with a new file passed via the daemon"""
		if not filename.startswith('/'):
			raise ValueError("filename must be an absolute path")

		self.logger.debug("Updating local file %s" % filename)

		message = []
		if data:
			data = json.read(data)
			fd, tfileName = tempfile.mkstemp()
			tfile = os.fdopen(fd, 'w')

			tfile.write(data)
			tfile.close()

			self.logger.debug("Finished writing temporary file %s" % tfileName)

			if os.path.isfile(filename):
				shutil.copystat(filename, tfileName)
				self.logger.debug("Copied existing permissions to temporary %s" % filename)

			dirname = os.path.dirname(filename)
			if not os.path.isdir(dirname):
				os.makedirs(dirname)
				self.logger.debug("Made the parent directory for %s" % filename)

			shutil.move(tfileName, filename)
			self.logger.debug("File written with new data")
			message.append("File %s overwritten with new data" % filename)

		else:
			self.logger.info("Did not update the file because no file data given")
			message.append("No new file data, so file not altered")

		if permissions:
			os.chmod(filename, int(permissions, 8))
			self.logger.debug("File permissions updated on %s" % filename)
			message.append("Permissions updated")

		message = "; ".join(message)
		return {'result':'ok', 'message':message}

	@cherrypy.expose
	def runLocalCommand(self, command):
		"""Runs a command on the system and returns it's output"""
		self.logger.debug("Executing local comand: %s" % command)

		status, output = commands.getstatusoutput(command)
		if status:
			status = os.WEXITSTATUS(status)

		return {'result':'ok', 'message':'Successfully executed your command', 'status':status, 'output':output}

def signalHandler(signum, frame):
	"""Turns signals into exceptions which should kick us out of engine.block()"""
	raise Exception("Interrupted by signal %s" % signum)

def registerHandlers():
	"""Sets handlers to initiate cleanup on signals"""
	toCatch = (
			signal.SIGHUP,
			signal.SIGINT,
			signal.SIGQUIT,
			signal.SIGTERM,
			signal.SIGALRM,
			signal.SIGUSR2,
			)

	for sig in toCatch:
		signal.signal(sig, signalHandler)

if __name__ == '__main__':
	logger = setupLogging()
	logger.info("Configuring cherrypy...")

	config = { 'log.screen':False, 'server.socket_port':1337, 'server.socket_host':'0.0.0.0' }
	config['log.error_file'] = "/var/log/drived.error"
	config['log.access_file'] = "/var/log/drived.access"

	config['checker.on'] = True
	config['environment'] = 'production'	#disables lots of random shit
	cherrypy.config.update( config )

	daemonizer = cherrypy.process.plugins.Daemonizer(cherrypy.engine, stdout='/tmp/daemonlog', stderr='/tmp/daemonlog')
	daemonizer.subscribe()

	root = Root()
	cherrypy.tree.mount(root, '/')
	cherrypy.engine.start()

	logger.info("Creating web interface...")
	interface = WebInterface()
	root.drived = interface
	root.control = interface

	logger.info("Startup successfull")
	registerHandlers()
	try:
		cherrypy.engine.block()
	except Exception, e:
		logger.warning("We are shutting down because we caught an exception: %s" % e)

		cherrypy.engine.stop()				#prevents any new connections from coming in
		cherrypy.engine.exit()

		logger.info("Exiting....")
		sys.exit(0)
