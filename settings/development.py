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
        'NAME': os.environ.setdefault('DEV_RDS_DB_NAME', 'theia_api'),
        'USER': os.environ.setdefault('DEV_RDS_USERNAME', 'theia'),
        'PASSWORD': os.environ.setdefault('DEV_RDS_PASSWORD', 'theia'),
        'HOST': os.environ.setdefault('RDS_HOSTNAME', '127.0.0.1'),
        'PORT': os.environ.setdefault('RDS_PORT', '5432'),
    }
}

# Logging
LOGGING['handlers']['file']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
if 'DJANGO_LOG_FILENAME' in os.environ:
    LOGGING['handlers']['file']['filename'] = os.environ['DJANGO_LOG_FILENAME']

# Redis
REDIS_URL = os.environ.setdefault('DEV_REDIS_URL', 'redis://')

# Cache
CACHES['default']['LOCATION'] = REDIS_URL

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
