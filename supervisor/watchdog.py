#!/usr/bin/env python

import logging
import os
import psutil
import time

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s watchdog %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S')

def get_server_process():
    for p in psutil.process_iter():
        if p.cmdline == ['/usr/bin/python', '/root/penguins/server/server.py']:
            return p

# log the next time these events happen
log_server_down = True
log_fresh = True

# every 5 seconds, check to see that the sever touched a file less than 5
# seconds ago. it tries to touch the file every second so it's really out to
# lunch if it hasn't done it yet.
while True:
    now = time.time()
    server = get_server_process()
    if server:
        log_server_down = True
        # the server process is running, so the monitor file should be current
        stat = os.stat('/tmp/server-monitor-alive')
        if now - stat[8] > 5:
            log_fresh = True
            # the server is out to lunch, kill it dead.
            # supervisor will restart it.
            server.kill(9)
            logging.error('monitor file is stale, killing server')
        elif log_fresh:
            logging.info('monitor file fresh')
            log_fresh = False
    elif log_server_down:
        logging.warning('server is not running')
        log_fresh = True
        log_server_down = False
    time.sleep(5)
