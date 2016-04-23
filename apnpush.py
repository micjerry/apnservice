import time, threading
import random
import logging

from  mickey.commonconf import APN_USE_SANDBOX, REDIS_IOS_PREFIX
import mickey.redis

from apns import APNs, Frame, Payload

if APN_USE_SANDBOX:
    _cert_file = 'cert_sand.pem'
    _key_file  = 'key_sand.pem'
else:
    _cert_file = 'cert.pem'
    _key_file = 'key.pem'

class ApnPush(object):
    
    def __init__(self):
        self._apns_enhanced = None
        
    def start(self):
        self._apns_enhanced = APNs(use_sandbox = True, cert_file = _cert_file, key_file = _key_file, enhanced = True)
        self._apns_enhanced.gateway_server.register_response_listener(self.response_listener)

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

        device_token = mickey.redis.read_from_redis(REDIS_IOS_PREFIX + user)
        if not device_token:
            logging.info("it is not ios user")
            return

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
            user = mickey.redis.read_from_redis(token_hex)
            mickey.redis.remove_from_redis(token_hex)
            if user:
                mickey.redis.remove_from_redis(REDIS_IOS_PREFIX + user)

        threading.Timer(86400, self.check_fails).start()

