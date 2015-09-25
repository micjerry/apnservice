import os
import sys

sys.path.append('/opt/webapps/libs')

import logging
import logging.handlers

import tornado
from tornado.options import define, options

import mickey.logutil
from mickey.daemon import Daemon

from apncomsumer import ApnConsumer
from apnpush import ApnPush

define("conf", default="/etc/mx_apps/app_apns/app_apns_is1.conf", help="Server config")
define("cmd", default="run", help="Command")
define("pidfile", default="/var/run/app_apns_is1.pid", help="Pid file")
define("logfile", default="/var/log/app_apns_is1", help="Log file")

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
        mickey.logutil.setuplognormal(options.logfile)
        apnserver = ApnServer()
        apnserver.start()

    def errorcmd(self):
        print("unkown command")
 
def micmain():
    tornado.options.parse_command_line()
    tornado.options.parse_config_file(options.conf)

    miceydamon = MickeyDamon(options.pidfile)
    handler = {}
    handler["start"] = miceydamon.start
    handler["stop"] = miceydamon.stop
    handler["restart"] = miceydamon.restart
    handler["run"] = miceydamon.run

    return handler.get(options.cmd, miceydamon.errorcmd)()

if __name__ == "__main__":
    micmain()
