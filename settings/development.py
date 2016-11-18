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

# Celery
CELERY_BROKER_URL = os.environ.setdefault('DEV_CELERY_BROKER_URL', 'redis://')
CELERY_RESULT_BACKEND = os.environ.setdefault('DEV_CELERY_RESULT_BACKEND', 'redis://')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Montreal'
