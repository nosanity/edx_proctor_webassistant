import logging
import json
import redis
import time

try:
    from amqp.exceptions import NotFound
except ImportError:
    pass

from celery import Celery
from kombu import Exchange

from edx_proctor_webassistant.settings import NOTIFICATIONS
from .broker_type import BrokerType

log = logging.getLogger(__name__)


class ProctorNotificator(object):
    _celery_app = None
    _exchange = None
    _redis_connection = None
    _redis_default_queue_id = 1

    _exchange_name = 'edx.proctoring.event'
    _routing_key = 'edx.proctoring.event'

    @classmethod
    def notify(cls, msg):
        msg['initiator'] = 'webassistant'
        msg['created'] = time.time()

        log.info('Publish notification: %s' % str(msg))

        broker_type = NOTIFICATIONS.get('BROKER_TYPE')

        if broker_type == BrokerType.AMQP:
            cls._send_to_amqp(msg)
        elif broker_type == BrokerType.REDIS:
            cls._send_to_redis(msg)
        else:
            raise Exception('Unknown broker type: %s' % str(broker_type))

    @classmethod
    def _send_to_amqp(cls, msg):
        celery_app = cls._get_celery_app()
        with celery_app.producer_or_acquire() as producer:
            with celery_app.connection_or_acquire() as conn:
                outgoing = conn.channel()
                try:
                    outgoing.exchange_declare(cls._exchange_name, "", passive=True)
                    producer.publish(msg,
                                     serializer='json',
                                     exchange=cls._get_exchange(),
                                     routing_key=cls._routing_key,
                                     retry=True,
                                     retry_policy={
                                         'interval_start': 0,  # First retry immediately,
                                         'interval_step': 2,  # then increase by 2s for every retry.
                                         'interval_max': 5,  # but don't exceed 5s between retries.
                                         'max_retries': 10
                                     })
                except NotFound:
                    log.error("Can't publish message. Exchange '%s' does not exist!" % cls._exchange_name)

    @classmethod
    def _get_celery_app(cls):
        if cls._celery_app is None:
            broker = NOTIFICATIONS.get('BROKER_URL', None)
            if broker:
                cls._celery_app = Celery('proctoring_notifications', broker=broker)
            else:
                raise Exception('BROKER_URL is not set!')
        return cls._celery_app

    @classmethod
    def _get_exchange(cls):
        if cls._exchange is None:
            cls._exchange = Exchange(cls._exchange_name, type='fanout', durable=True)
        return cls._exchange

    @classmethod
    def _get_redis_client(cls):
        if cls._redis_connection is None:
            cls._redis_connection = redis.from_url(NOTIFICATIONS.get('BROKER_URL'))
        return cls._redis_connection

    @classmethod
    def _get_redis_queues(cls):
        queues_key = '%s.daemons' % cls._exchange_name
        redis_conn = cls._get_redis_client()
        queues_dict = redis_conn.hgetall(queues_key)
        log.info('Queues in redis [key %s]: %s' % (queues_key, str(queues_dict)))
        res = []
        if queues_dict:
            res = [int(v) for k, v in queues_dict.items()]
        if cls._redis_default_queue_id not in res:
            # always send message at least to the default queue
            # additional check to avoid loss some messages
            # in case if LMS is already started but notification daemon not yet
            res.insert(0, cls._redis_default_queue_id)
        return sorted(res)

    @classmethod
    def _send_to_redis(cls, msg):
        max_retries = 5
        current_attempt = 1

        while True:
            try:
                redis_conn = cls._get_redis_client()
                redis_queues = ['%s.%d' % (cls._exchange_name, int(queue_id))
                                for queue_id in cls._get_redis_queues()]
                log.info('Try to push message to the queues: %s' % str(redis_queues))
                for queue_name in redis_queues:
                    redis_conn.lpush(queue_name, json.dumps(msg))
                return
            except redis.ConnectionError:
                if current_attempt > max_retries:
                    raise
                else:
                    time.sleep(current_attempt * 2)
                    current_attempt += 1
