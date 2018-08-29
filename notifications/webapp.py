# encoding: utf-8

import logging
import time
import tornado.web
import tormysql
import pymysql
import uuid

from collections import OrderedDict
from datetime import datetime
from tornado import gen
from raven.contrib.tornado import AsyncSentryClient
from sockjs.tornado import SockJSRouter, SockJSConnection


logger = logging.getLogger('notifications.web')


class NotificationWebApp(tornado.web.Application):

    def __init__(self, db_settings, url, raven_dsn=None):
        self.broker_connected = False
        if raven_dsn:
            self.sentry_client = AsyncSentryClient(dsn=raven_dsn)
        self.db_pool = self._connect_to_db(db_settings)
        self.notifications_router = NotificationsRouter(NotificationsConnection, url)
        self.courses = {}
        super(NotificationWebApp, self).__init__(self.notifications_router.urls)

    def _connect_to_db(self, settings):
        return tormysql.ConnectionPool(
            max_connections=20,  # max open connections
            idle_seconds=7200,   # conntion idle timeout time, 0 is not timeout
            wait_connection_timeout=3,  # wait connection timeout
            host=settings['HOST'],
            port=int(settings['PORT']),
            user=settings['USER'],
            passwd=settings['PASSWORD'],
            db=settings['NAME'],
            charset="utf8",
            cursorclass=pymysql.cursors.DictCursor
        )

    def notify(self, message):
        initiator = message.get('initiator')
        if initiator:
            if initiator == 'edx.proctoring':
                self._process_edx_message(message)
            else:
                self._notify_participants(message)

    def _notify_participants(self, message):
        course_event_id = message.get('course_event_id')
        if course_event_id:
            course_event_id = int(course_event_id)
            logger.debug('Send message to client (course_event_id: %d, message_body: %s)' % (course_event_id, message))
            self.notifications_router.notify_participants(course_event_id, message)

    @gen.coroutine
    def _process_edx_message(self, message):
        course_id = message.get('course_id')
        course_event_id = message.get('course_event_id')
        exam_code = message.get('code')
        new_status = message.get('status')
        action = message.get('action')
        tm = message.get('created', time.time())
        dt = datetime.fromtimestamp(tm) if tm else None

        if not course_id or not exam_code or not course_event_id:
            return

        with (yield self.db_pool.Connection()) as conn:
            with conn.cursor() as cursor:
                if course_id not in self.courses:
                    yield cursor.execute("SELECT * FROM proctoring_course WHERE display_name=%s", (course_id,))
                    proctoring_course = cursor.fetchone()
                    if not proctoring_course:
                        logger.warning("Course '%s' not found", course_id)
                        return
                    self.courses[course_id] = proctoring_course['id']

                yield cursor.execute("SELECT * FROM proctoring_exam WHERE course_id=%s AND exam_code=%s",
                                     (self.courses[course_id], exam_code))
                proctoring_exam = cursor.fetchone()
                if proctoring_exam:
                    notify_participants = True

                    if action == 'change_status' and new_status\
                            and proctoring_exam['attempt_status'] != new_status and dt\
                            and (not proctoring_exam['attempt_status_updated']
                                 or dt > proctoring_exam['attempt_status_updated']):
                        data_to_update = OrderedDict()

                        if proctoring_exam['attempt_status'] == 'ready_to_start' and new_status == 'started':
                            data_to_update['actual_start_date'] = str(datetime.now())
                        if (proctoring_exam['attempt_status'] == 'started' and new_status == 'submitted') \
                              or (proctoring_exam['attempt_status'] == 'ready_to_submit' and new_status == 'submitted'):
                            dt_end = datetime.now()
                            data_to_update['actual_end_date'] = str(dt_end)
                            message['actual_end_date'] = dt_end.isoformat() + 'Z'
                        data_to_update['attempt_status'] = new_status
                        data_to_update['attempt_status_updated'] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                        data_to_update['last_poll'] = str(datetime.now())

                        try:
                            sql = "UPDATE proctoring_exam SET " + ', '.join([k + '=%s' for k in data_to_update.keys()])\
                                  + " WHERE id=" + str(proctoring_exam['id'])
                            yield cursor.execute(sql, tuple(data_to_update.values()))
                        except Exception as e:
                            notify_participants = False
                            logger.warning("Can't update exam [id=%s]: %s", proctoring_exam['id'], str(e))
                            yield conn.rollback()
                        else:
                            logger.info("Exam [id=%s] was updated. Previous status: %s (%s). New status: %s (%s)",
                                        proctoring_exam['id'], proctoring_exam['attempt_status'],
                                        str(proctoring_exam['attempt_status_updated']), new_status,
                                        data_to_update['attempt_status_updated'])
                            yield conn.commit()
                    elif action == 'new_user_session':
                        try:
                            message_data = message.get('data', None)
                            if not message_data:
                                return

                            message['data']['timestamp'] = tm

                            sess_data_session_id = message_data.get('session_id', '')
                            sess_data_user_agent = message_data.get('user_agent', '')
                            sess_data_browser = message_data.get('browser', '')
                            sess_data_os = message_data.get('os', '')
                            sess_data_ip_address = message_data.get('ip_address', '')

                            data_to_insert = OrderedDict([
                                ('session_id', sess_data_session_id),
                                ('user_agent', sess_data_user_agent),
                                ('browser', sess_data_browser),
                                ('os', sess_data_os),
                                ('ip_address', sess_data_ip_address),
                                ('timestamp', tm),
                                ('exam_id', proctoring_exam['id']),
                            ])
                            sql = "INSERT INTO proctoring_usersession(session_id, user_agent, browser, os, " \
                                  "ip_address, timestamp, exam_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                            yield cursor.execute(sql, tuple(data_to_insert.values()))
                        except Exception as e:
                            notify_participants = False
                            logger.warning("Can't insert user session [exam id=%s]: %s",
                                           proctoring_exam['id'], str(e))
                            yield conn.rollback()
                        else:
                            logger.info("User session was added: session id: %s, browser: %s, os: %s,"
                                        " IP: %s, timestamp: %s, exam_id: %s",
                                        sess_data_session_id, sess_data_browser, sess_data_os, sess_data_ip_address,
                                        str(tm), str(proctoring_exam['id']))
                            yield conn.commit()

                    if notify_participants:
                        self._notify_participants(message)

    def on_broker_connected(self):
        self.broker_connected = True
        logger.info('AMQP borker connected')

    def on_broker_closed(self):
        logger.info('AMQP borker closed')
        self.broker_connected = False


class NotificationsConnection(SockJSConnection):
    participants = None

    def __init__(self, session):
        self.course_event_id = None
        self.connection_id = None
        super(NotificationsConnection, self).__init__(session)

    def on_open(self, request):
        course_event_id = request.get_argument('course_event_id')
        if course_event_id:
            self.course_event_id = int(course_event_id)
            self.connection_id = uuid.uuid4()
            logger.info('Notification connection was opened # %s : %s (course_event_id: %s)',
                        self.connection_id, request.path, self.course_event_id)
            if self.course_event_id not in self.participants:
                self.participants[self.course_event_id] = set()
            self.participants[self.course_event_id].add(self)

    def on_message(self, message):
        pass

    def on_server_message(self, data):
        self.send(data)

    def on_close(self):
        logger.info('Notification connection was closed # %s (course_event_id: %s)',
                    self.connection_id, self.course_event_id)
        if self.course_event_id:
            self.participants[self.course_event_id].remove(self)


class NotificationsRouter(SockJSRouter):

    def __init__(self, *args, **kwargs):
        super(NotificationsRouter, self).__init__(*args, **kwargs)
        self._connection.participants = {}

    def notify_participants(self, course_event_id, msg):
        participants = self._connection.participants.get(int(course_event_id), [])
        if participants:
            logger.info('Broadcast messages to participants (course_event_id: %s)',
                        course_event_id)
            self.broadcast(participants, msg)
        else:
            logger.info('Participants not found (course_event_id: %s)', course_event_id)
