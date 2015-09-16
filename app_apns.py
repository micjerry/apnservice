import os
import sys

sys.path.append('/opt/webapps/libs')

import logging
import logging.handlers

import mickey.logutil
from mickey.daemon import Daemon

from apncomsumer import ApnConsumer
from apnpush import ApnPush

class ApnServer(object):
    def __init__(self):
        self._apnconsumer = None
        self._apnpush = None
        self._amurl = 'amqp://mxpub:mhearts2015@localhost:6500/%2F'

    def start(self):
        self._apnpush = ApnPush()
        self._apnpush.start()
        self._apnconsumer = ApnConsumer(self._apnpush, self._amurl)
        self._apnconsumer.run()
        

class MickeyDamon(Daemon):
    def run(self):
        mickey.logutil.setuplognormal()
        apnserver = ApnServer()
        apnserver.start()

    def errorcmd(self):
        print("unkown command")
 
def micmain():
    if len(sys.argv) < 2:
        print("invalid command")
        return

    pid_file_name = "/var/run/" + sys.argv[0].replace(".py", ".pid")
    miceydamon = MickeyDamon(pid_file_name)
    handler = {}
    handler["start"] = miceydamon.start
    handler["stop"] = miceydamon.stop
    handler["restart"] = miceydamon.restart
    handler["run"] = miceydamon.run

    return handler.get(sys.argv[1],miceydamon.errorcmd)()

if __name__ == "__main__":
    micmain()
