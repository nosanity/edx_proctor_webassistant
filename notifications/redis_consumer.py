# encoding: utf-8

import json
import logging
import asyncio
import aioredis
import tornado
import traceback

logger = logging.getLogger('notifications.redis')


class RedisConsumer(object):
    EXCHANGE = 'edx.proctoring.event'

    def __init__(self, application, daemon_id, broker_url):
        """Create a new instance of the consumer class, passing in the AMQP
        URL used to connect to RabbitMQ

        :param tornado.web.Application application
        :param int daemon_id
        :param str broker_url: The AMQP url to connect with

        """
        self._application = application
        self._daemon_id = daemon_id
        self._pool = None
        self._url = broker_url
        self._main_tsk = None
        self._heartbeat_tsk = None
        self._heartbeat_timeout = 15  # seconds
        self._heartbeat_sleep = None
        self._queue = '%s.%s' % (self.EXCHANGE, str(daemon_id))
        self._queue_id = 'd_' + str(self._daemon_id)
        self._queue_for_daemons = '%s.daemons' % self.EXCHANGE
        self._closing = False

    async def run(self):
        try:
            logger.info('Connecting to Redis: %s', self._url)
            self._pool = await aioredis.create_redis_pool(self._url, timeout=5)
            # heartbeat is a process that check existence of queue_id in the special auxiliary variable in redis
            # in case if this variable will be removed somehow (may be manually)
            # it will be re-created by this heartbeat process
            self._heartbeat_tsk = asyncio.ensure_future(self._heartbeat())
            self._application.on_broker_connected()
            self._main_tsk = asyncio.ensure_future(self._reader())
        except ConnectionError as e:
            logger.error("Can't establish connections: " + str(e))
            self._stop_instance(e)
        except Exception as e:
            self._stop_instance(e)

    async def stop(self):
        logger.info('Stopping Redis consumer')
        self._closing = True

        # suggest ignore unsubscribe
        # if we stop daemon manually - producer will continue sending message
        # and after the next start daemon will fetch all messages
        # that may avoid loss some messages
        # so if you decide that some daemon is not needed anymore
        # you should remove all data from redis manually:
        # >> HDEL edx.proctoring.event.daemons d_N
        # >> DEL edx.proctoring.event.N
        # where N is DAEMON_ID
        #await self._unsubscribe()

        self._pool.close()
        self._cancel_heartbeat()
        await self._main_tsk
        await self._heartbeat_tsk
        self._application.on_broker_closed()
        logger.info('Redis consumer is stopped')

    async def _check_and_subscribe(self):
        with await self._pool as r:
            try:
                queues_dict = await r.hgetall(self._queue_for_daemons)
                queues_lst = [int(q.decode("utf-8")) for q in queues_dict.values()] if queues_dict else []
                if not queues_lst or int(self._daemon_id) not in queues_lst:
                    logger.info('Try to subscribe to the queue with ID: %s' % str(self._daemon_id))
                    await r.hmset(self._queue_for_daemons, self._queue_id, self._daemon_id)
            except aioredis.errors.ConnectionForcedCloseError as e:
                if not self._closing:
                    raise e
                else:
                    return
            except aioredis.errors.ConnectionClosedError as e:
                self._stop_instance(e)

    async def _unsubscribe(self):
        with await self._pool as r:
            logger.info('Try to unsubscribe from the queue with ID: %s' % str(self._daemon_id))
            await r.hdel(self._queue_for_daemons, self._queue_id)

    async def _reader(self):
        while not self._closing:
            with await self._pool as r:
                try:
                    msg = await r.brpop(self._queue, timeout=0)
                    try:
                        json_body = json.loads(msg[1].decode('utf-8'))
                        if json_body and not isinstance(json_body, dict):
                            raise ValueError('Message is not dictionary: %s' % type(json_body))
                    except (ValueError, TypeError, AttributeError, KeyError):
                        json_body = None
                        logger.exception("Message from Redis isn't valid JSON or not dictionary: %s" % str(msg))
                    if json_body:
                        self._application.notify(json_body)
                except aioredis.errors.ConnectionForcedCloseError as e:
                    if not self._closing:
                        raise e
                    else:
                        logger.info('Consumer reader stopped')
                        return
                except aioredis.errors.ConnectionClosedError as e:
                    self._stop_instance(e)

    async def _heartbeat(self):
        while not self._closing:
            await self._check_and_subscribe()
            self._heartbeat_sleep = self._make_sleep()
            await self._heartbeat_sleep(self._heartbeat_timeout)

    def _cancel_heartbeat(self):
        if self._heartbeat_sleep and hasattr(self._heartbeat_sleep, 'cancel_all'):
            self._heartbeat_sleep.cancel_all()

    def _make_sleep(self):
        async def sleep(delay, result=None, *, loop=None):
            core_sleep = asyncio.sleep(delay, result=result, loop=loop)
            task = asyncio.ensure_future(core_sleep)
            sleep.tasks.add(task)
            try:
                return await task
            except asyncio.CancelledError:
                return result
            finally:
                sleep.tasks.remove(task)

        sleep.tasks = set()
        sleep.cancel_all = lambda: sum(task.cancel() for task in sleep.tasks)
        return sleep

    def _stop_instance(self, err):
        traceback.print_exc()
        logger.info('Consumer error: ' + str(err))
        tornado.ioloop.IOLoop.instance().stop()
