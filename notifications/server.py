# encoding: utf-8

import signal
import logging.config

from tornado import ioloop, gen
from tornado.httpserver import HTTPServer

from .webapp import NotificationWebApp
from .broker_type import BrokerType


logger = logging.getLogger('notifications')


class NotificationServer(object):

    def __init__(self, broker_type, webport, daemon_id, web_url, broker_url, db_settings=None, raven_dsn=None):
        self.broker_type = broker_type
        self.webport = webport
        self.broker_url = broker_url
        self._ioloop_instance = ioloop.IOLoop.instance()

        try:
            daemon_id = int(daemon_id)
            if daemon_id < 1 or daemon_id > 10:
                raise ValueError('Invalid value')
        except ValueError:
            raise Exception('Invalid DAEMON_ID param. Must be integer: 1 - 10')

        self.web_app = NotificationWebApp(db_settings, web_url, raven_dsn)
        if self.broker_type == BrokerType.AMQP:
            from .amqp_consumer import AMQPConsumer
            self.consumer = AMQPConsumer(self.web_app, daemon_id, broker_url)
        elif self.broker_type == BrokerType.REDIS:
            from .redis_consumer import RedisConsumer
            self.consumer = RedisConsumer(self.web_app, daemon_id, broker_url)
        else:
            raise Exception('Unknown broker type: %s' % str(self.broker_type))
        self.web_server = HTTPServer(self.web_app)
        self.is_alive = False

    def start(self):
        self.web_app.listen(self.webport)
        logger.info('Web server listening to %s', self.webport)

        signal.signal(signal.SIGTERM, self.sig_handler)
        signal.signal(signal.SIGINT, self.sig_handler)

        # timeout in 10 seconds because web frontend
        # tries to reconnect sockjs connection every 3 seconds
        # and to avoid miss events AMQP connection should be established
        # only all listeners will be connected
        self._ioloop_instance.call_later(10, self._run_consumer)

        logger.info('IOLoop start')
        self.is_alive = True
        self._ioloop_instance.start()

    def _run_consumer(self):
        self._execute_consumer_fn(self.consumer.run)
        logger.info('Consumer started')

    def sig_handler(self, sig, frame):
        logging.warning('Caught signal: %s', sig)
        logger.info('Try to stop notifications server')
        ioloop.IOLoop.instance().add_callback(self.stop)

    def _execute_consumer_fn(self, fn):
        if self.broker_type == BrokerType.AMQP:
            fn()
        elif self.broker_type == BrokerType.REDIS:
            self._ioloop_instance.add_callback(fn)

    @gen.coroutine
    def stop(self):
        self._execute_consumer_fn(self.consumer.stop)
        while self.web_app.broker_connected:
            logger.info('Waiting until the Consumer will stop.')
            yield gen.sleep(0.1)
        self.web_server.stop()
        self._ioloop_instance.stop()
        logger.info('Notifications stopped')
