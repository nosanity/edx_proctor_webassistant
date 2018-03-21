# encoding: utf-8
import logging
import time
import tornado
import os

from notifications.server import NotificationServer
from edx_proctor_webassistant.settings import NOTIFICATIONS, LOGGING, RAVEN_CONFIG, DATABASES, TIME_ZONE


def main():
    os.environ['TZ'] = TIME_ZONE
    time.tzset()

    logger = logging.getLogger('notifications')

    if 'SERVER_PORT' not in NOTIFICATIONS or 'BROKER_URL' not in NOTIFICATIONS:
        raise Exception('Please set \'NOTIFICATIONS\' dict in the settings.py')

    logger.info('Start notifications server (Tornado Version {tornado_version})'.format(tornado_version=tornado.version))
    server = NotificationServer(NOTIFICATIONS['SERVER_PORT'], daemon_id=NOTIFICATIONS['DAEMON_ID'],
                                web_url=NOTIFICATIONS['WEB_URL'], broker_url=NOTIFICATIONS['BROKER_URL'],
                                db_settings=DATABASES['default'], raven_dsn=RAVEN_CONFIG.get('dsn'))
    try:
        server.start()
    except Exception as e:
        print(e)
        logger.exception('%s', e)
        server.stop()
        raise


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING)
    main()
