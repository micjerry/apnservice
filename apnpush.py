import time, threading
import random
import logging
from redis.sentinel import Sentinel
from apns import APNs, Frame, Payload

class ApnPush(object):
    IOS_KEY_FLAG = 'ioskey'
    
    def __init__(self):
        self._apns_enhanced = None
        self._sentinel = None
        self._sentinel_salve = None
        self._sentinel_master = None
        
    def start(self):
        self._apns_enhanced = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem', enhanced=True)
        self._apns_enhanced.gateway_server.register_response_listener(self.response_listener)
        self._sentinel = Sentinel([('localhost', 26379)], socket_timeout = 1)
        self._sentinel_salve  = self._sentinel.slave_for('master', socket_timeout = 0.5)
        self._sentinel_master = self._sentinel.master_for('master', socket_timeout = 0.5)

        self.check_fails()

    def push(self, event):
        logging.info("begin to push %r" % event)
        user = event.get("user", "")
        user = user.replace("temp", "")
        msg_type = event.get("msg_type", "other")
        msg = event.get("msg", "")
        if not user:
            logging.info("invalid message received")
            return

        device_token = self._sentinel_salve.get(self.IOS_KEY_FLAG + user)
        if not device_token:
            logging.info("it is not ios user")
            return

        device_token = device_token.decode("utf-8")
        logging.info("begin to push %s" % device_token)

        push_msg = ""
        if not msg:
            if msg_type == "call":
                push_msg = "您有一个未接来电"
            else:
                push_msg = "您有一条明信消息"
        else:
            push_msg = msg
                 
        payload = Payload(alert = push_msg, sound = "default", badge = 1)
        identifier = random.getrandbits(32)
        self._apns_enhanced.gateway_server.send_notification(device_token, payload, identifier=identifier)

    def response_listener(self, error_response):
        logging.debug('client get error-response:' + str(error_response))

    def stop(self):
        if self._apns_enhanced:
            self._apns_enhanced.gateway_server.force_close()

    def check_fails(self):
        logging.info("start check fails:")
        feedback_connection = APNs(use_sandbox=True, cert_file='cert.pem', key_file='key.pem')
        for (token_hex, fail_time) in feedback_connection.feedback_server.items():
            user = self._sentinel_salve.get(token_hex)
            self._sentinel_master.delete(token_hex)
            if user:
                user_key = IOS_KEY_FLAG + iostoken.decode("utf-8")
                self._sentinel_master.delete(user_key)

        threading.Timer(86400, self.check_fails).start()

