import os

from .common import *

###############################################################################
#                             Development Settings                            #
###############################################################################

DEBUG = True

ALLOWED_HOSTS = ['*',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'theia_api',
        'USER': 'theia',
        'PASSWORD': 'theia',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

# Redis
REDIS_DB = 0
REDIS_DOMAIN = 'localhost'
REDIS_URL = '{}{}:{}/{}'.format(
    REDIS_PROTOCOL,
    REDIS_DOMAIN,
    REDIS_PORT,
    REDIS_DB)

# Cache
CACHES['default']['LOCATION'] = REDIS_URL

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Dropbox settings
DROPBOX_APP_KEY = os.environ['DEV_DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['DEV_DROPBOX_APP_SECRET']
DROPBOX_TOKEN = os.environ['DEV_DROPBOX_TOKEN']
DROPBOX_EXPORT_FOLDER = '/jsgroup-api-dev'

