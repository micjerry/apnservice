import logging
import pika
import json

from redis.sentinel import Sentinel

class ApnConsumer(object):
    EXCHANGE      = 'apppush'
    EXCHANGE_TYPE = 'direct'
    QUEUE         = 'apnspecific'
    ROUTING_KEY   = 'pushiosdevice'

    def __init__(self, apnpush, amqp_url):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._apns = apnpush

    def connect(self):
        logging.info('Connecting to %s' % self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close = False)

    def on_connection_open(self, unused_connection):
        logging.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        logging.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            logging.error('Connection closed, reopening in 5 seconds: (%s) %s' % (reply_code, reply_text))
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        self._connection.ioloop.stop()
        if not self._closing:
            self._connection = self.connect()
            self._connection.ioloop.start()

    def open_channel(self):
        logging.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        logging.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        logging.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        logging.error('Channel %i was closed: (%s) %s' % (channel, reply_code, reply_text))
        self._connection.close()

    def setup_exchange(self, exchange_name):
        logging.info('Declaring exchange %s' % exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self.EXCHANGE_TYPE)

    def on_exchange_declareok(self, unused_frame):
        logging.info('Exchange declared')
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        logging.info('Declaring queue %s' % queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name)

    def on_queue_declareok(self, method_frame):
        logging.info('Binding %s to %s with %s' % (self.EXCHANGE, self.QUEUE, self.ROUTING_KEY))
        self._channel.queue_bind(self.on_bindok, self.QUEUE,
                                 self.EXCHANGE, self.ROUTING_KEY)
    
    def on_bindok(self, unused_frame):
        logging.info('Queue bound')
        self.start_consuming()

    def start_consuming(self):
        logging.info('Issuing consumer')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self.QUEUE,
                                                         no_ack = True)

    def add_on_cancel_callback(self):
        logging.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        logging.info('Consumer was cancelled remotely, shutting down: %r' % method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, unused_channel, basic_deliver, properties, body):
        logging.info('Received message %s' % body)
        event = json.loads(body.decode("utf-8"))
        self._apns.push(event)
                

    def stop_consuming(self):
        if self._channel:
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def on_cancelok(self, unused_frame):
        logging.info('RabbitMQ acknowledged the cancellation of the consumer')
        self.close_channel()

    def close_channel(self):
        logging.info('Closing the channel')
        self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        logging.info("Stopping")
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        logging.info("Stopped")

    def close_connection(self):
        logging.info('Closing connection')
        self._connection.close()


