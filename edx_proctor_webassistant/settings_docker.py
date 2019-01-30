# -*- coding: utf-8 -*-
"""
Django local_settings for tpl_site project.
"""
import os


DEBUG = str(os.getenv('DEBUG', False))
PIPELINE_ENABLED = False

if os.getenv('SECRET_KEY'):
    SECRET_KEY = os.getenv('SECRET_KEY', '__DEFINE_ME__')

BOWER_PATH = '/usr/lib/node_modules/bower/bin/bower'
PIPELINE_YUGLIFY_BINARY = '/edx/app/epw/node_modules/.bin/yuglify'

STATIC_ROOT = os.getenv('STATIC_ROOT', '/opt/static')

PLATFORM_BASE_DOMAIN = os.getenv('PLATFORM_BASE_DOMAIN', 'example.com')
PLATFORM_SCHEME = os.getenv('PLATFORM_SCHEME', 'https')
SSO_TP_URL = os.getenv( 'SSO_TP_URL', '{}://{}.{}'.format(PLATFORM_SCHEME, os.getenv('SUB_DOMAIN_SSO', 'sso'), PLATFORM_BASE_DOMAIN))
SSO_PWA_URL = SSO_TP_URL
SOCIAL_AUTH_SSO_TP_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_SSO_TP_OAUTH2_KEY', '__DEFINE_ME__')
SOCIAL_AUTH_SSO_TP_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_SSO_TP_OAUTH2_SECRET', '__DEFINE_ME__')
REDIRECT_IS_HTTPS = str(os.getenv('REDIRECT_IS_HTTPS', False))

EDX_URL = os.getenv('EDX_URL', '{}://{}.{}'.format(PLATFORM_SCHEME, os.getenv('SUB_DOMAIN_LMS', 'courses'), PLATFORM_BASE_DOMAIN))
EDX_API_KEY = os.getenv('EDX_API_KEY', '__DEFINE_ME__')

AUTH_SESSION_COOKIE_DOMAIN = os.getenv('AUTH_SESSION_COOKIE_DOMAIN', '.{}'.format(PLATFORM_BASE_DOMAIN))

GRAPPELLI_ADMIN_TITLE = os.getenv('GRAPPELLI_ADMIN_TITLE', 'Webassistant')

COURSE_ID_SLASH_SEPARATED = str(os.getenv('COURSE_ID_SLASH_SEPARATED', False)) == 'True'

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.getenv('EPW_MYSQL_HOST', 'mariadb'),
        "NAME": os.getenv('EPW_MYSQL_NAME', 'epw'),
        "USER": os.getenv('EPW_MYSQL_USER', 'epw'),
        "PASSWORD": os.getenv('EPW_MYSQL_PASSWORD', 'epw'),
        "PORT": os.getenv('EPW_MYSQL_PORT', '3306'),
     }
}

NOTIFICATIONS = {
    "SERVER_PORT": int(os.getenv("SERVER_PORT", 8137)),
    "BROKER_URL": os.getenv('BROKER_URL', 'amqp://epw:{}@rabbitmq:5672/'.format(os.getenv('EPW_BROKER_PASSWORD', 'epw'))),
    "DAEMON_ID": "1",
    "WEB_URL": "/notifications"
}

LOGO_NAME = 'https://s31333.cdn.ngenix.net/fd95ff/732fb95c/img/logo-light.png'

RAVEN_DSN = os.getenv('DSN', None)

# ==== Raven =================================================================
#RAVEN_CLIENT = None
if RAVEN_DSN:
    try:
        import os
        import raven
        from raven.transport.requests import RequestsHTTPTransport
        from raven import Client
        RAVEN_CONFIG = {
            'dsn': RAVEN_DSN,
            'transport': RequestsHTTPTransport,
        }
        RAVEN_CLIENT = Client(**RAVEN_CONFIG)
    except ImportError:
        print("Couldn't enable Raven. Exception will not be sent to Sentry")

SUPERUSER_USERNAME = os.getenv('SUPERUSER_USERNAME', 'admin')
SUPERUSER_EMAIL = os.getenv('SUPERUSER_EMAIL', 'admin@{}'.format(AUTH_SESSION_COOKIE_DOMAIN.strip('.')))
SUPERUSER_PASSWORD = os.getenv('SUPERUSER_PASSWORD')

