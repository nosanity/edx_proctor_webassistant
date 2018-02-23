# -*- coding: utf-8 -*-
"""
Django settings for edx_proctor_webassistant project.

Generated by 'django-admin startproject' using Django 1.8.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

SECRET_KEY = '<ADD_YOUR_SECRET_KEY_IN_LOCAL_SETTINGS>'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'djangobower',
    'pipeline',
    'ws4redis',
    'rest_framework',

    'person',
    'proctoring',
    'ui',
    'journaling',
    'social.apps.django_app.default',
    'sso_auth',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'edx_proctor_webassistant.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates/', ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ws4redis.context_processors.default',
                "django.core.context_processors.request",
            ],
        },
    },
]

# WSGI_APPLICATION = 'edx_proctor_webassistant.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

#LANGUAGE_CODE = 'en-us'
LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


LOGIN_URL = LOGIN_REDIRECT_URL = LOGOUT_REDIRECT_URL = "/"

# Auth settings with/without sso
AUTH_BACKEND_NAME = 'sso_npoed-oauth2'
SSO_ENABLED = True

if SSO_ENABLED:
    TEMPLATES[0]['OPTIONS']['context_processors'] += [
        'social.apps.django_app.context_processors.backends',
        'social.apps.django_app.context_processors.login_redirect',
    ]
    try:
        from sso_auth.social_auth_settings import *
    except ImportError:
        print "CRITICAL: Social auth enabled."
        "But  social_auth_settings.py didn't specified"
        exit()

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR + '/static/'
STATICFILES_FINDERS = ('django.contrib.staticfiles.finders.FileSystemFinder',
                       'django.contrib.staticfiles.finders.AppDirectoriesFinder',
                       'djangobower.finders.BowerFinder',
                       'pipeline.finders.PipelineFinder',)
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), '..',
                 'components/bower_components'),
)

# Bower settings
# https://github.com/nvbn/django-bower
BOWER_COMPONENTS_ROOT = BASE_DIR + '/components/'

BOWER_INSTALLED_APPS = (
    'angular#1.5.8',
    'angular-route#1.5.8',
    'angular-animate#1.5.8',
    'angular-sanitize#1.5.8',
    'jquery#3.1.1',
    'bootstrap#3.3.7',
    'ng-table#0.8.3',
    'angular-bootstrap#2.1.4',
    'angular-translate#2.12.1',
    'angular-translate-storage-local#2.12.1',
    'angular-translate-loader-static-files#2.12.1',
)

# Pipeline
# PIPELINE_ENABLED = True
PIPELINE_DISABLE_WRAPPER = True
PIPELINE_CSS = {
    'css': {
        'source_filenames': (
            'bootstrap/dist/css/bootstrap.min.css',
            'ng-table/dist/ng-table.css',
            'css/*.css',
        ),
        'output_filename': 'css/styles.css',
        'extra_context': {
            'media': 'screen,projection',
        },
    },
}
PIPELINE_JS = {
    'js': {
        'source_filenames': (
            'jquery/dist/jquery.min.js',
            'bootstrap/dist/js/bootstrap.js',
            'angular/angular.js',
            'angular-animate/angular-animate.min.js',
            'angular-route/angular-route.min.js',
            'angular-cookies/angular-cookies.min.js',
            'angular-sanitize/angular-sanitize.min.js',
            'ng-table/dist/ng-table.min.js',
            'angular-bootstrap/ui-bootstrap.js',
            'angular-translate/angular-translate.min.js',
            'angular-translate-storage-local/angular-translate-storage-local.min.js',
            'angular-translate-storage-cookie/angular-translate-storage-cookie.min.js',
            'angular-translate-loader-static-files/angular-translate-loader-static-files.min.js',
            'js/app/app.js',
            'js/lib/checklist-model.js',
            'js/app/common/modules/websocket.js',
            'js/app/common/modules/auth.js',
            'js/app/common/modules/backend_api.js',
            'js/app/common/modules/session.js',
            'js/app/common/modules/i18n.js',
            'js/app/common/modules/date.js',
            'js/app/common/helpers.js',
        ),
        'output_filename': 'js/app.js',
    }
}

# Websocket settings
# http://django-websocket-redis.readthedocs.org/en/latest/installation.html
#
WEBSOCKET_EXAM_CHANNEL = 'attempts'
WEBSOCKET_URL = '/ws/'
WS4REDIS_CONNECTION = {
    'host': 'localhost',
    'port': 6379,
    # 'db': 0,
    # 'password': 'verysecret',
}
WS4REDIS_EXPIRE = 5
WS4REDIS_PREFIX = 'ws'
WSGI_APPLICATION = 'ws4redis.django_runserver.application'
WS4REDIS_ALLOWED_CHANNELS = (
    'attempts'
)
WS4REDIS_HEARTBEAT = '--heartbeat--'

# Config for Single Page Application
SPA_CONFIG = {
    "sso_enabled": SSO_ENABLED,
    # "language": "en",
    "language": "en",
    "allow_language_change": False,
    "supported_languages": ['en']
}

try:
    from settings_local import *
except ImportError:
    print "CRITICAL: You must specify settings_local.py"
    exit()

INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django.raven_compat',
)

FINAL_EXAM_STATUSES = ['error', 'verified', 'rejected', 'deleted_in_edx']
