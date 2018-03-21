# encoding: utf-8

import signal
import logging.config

from tornado import ioloop, gen
from tornado.httpserver import HTTPServer

from .amqp_consumer import AMQPConsumer
from .webapp import NotificationWebApp


logger = logging.getLogger('notifications')


class NotificationServer(object):

    def __init__(self, webport, daemon_id, web_url, broker_url, db_settings=None, raven_dsn=None):
        self.webport = webport
        self.broker_url = broker_url
        self._ioloop_instance = ioloop.IOLoop.instance()

        self.web_app = NotificationWebApp(db_settings, web_url, raven_dsn)
        self.amqp_consumer = AMQPConsumer(self.web_app, daemon_id, broker_url)
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
        self._ioloop_instance.call_later(10, self._run_amqp_consumer)

        logger.info('IOLoop start')
        self.is_alive = True
        self._ioloop_instance.start()

    def _run_amqp_consumer(self):
        self.amqp_consumer.run()
        logger.info('AMQPConsumer started')

    def sig_handler(self, sig, frame):
        logging.warning('Caught signal: %s', sig)
        logger.info('Try to stop notifications server')
        ioloop.IOLoop.instance().add_callback(self.stop)

    @gen.coroutine
    def stop(self):
        self.amqp_consumer.stop()
        while self.web_app.broker_connected:
            logger.info('Waiting until the AMQPConsumer will stop.')
            yield gen.sleep(0.1)
        self.web_server.stop()
        self._ioloop_instance.stop()
        logger.info('Notifications stopped')
