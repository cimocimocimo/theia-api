import os

from .common import *

###############################################################################
#                               Testing Settings                              #
###############################################################################

# NOTE: this is only for testing in the AWS Elastic Beanstalk environment.
# This isn't for running unit tests.

DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'api.testing.theiacouture.com',
    'jsgroup-api-test.us-east-1.elasticbeanstalk.com',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'api_testing',
        'USER': 'api_testing',
        'PASSWORD': os.environ['TEST_RDS_PASSWORD'],
        'HOST': RDS_HOSTNAME,
        'PORT': RDS_PORT,
    }
}

# Redis
REDIS_DB = 10
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
DROPBOX_APP_KEY = os.environ['TEST_DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['TEST_DROPBOX_APP_SECRET']
DROPBOX_TOKEN = os.environ['TEST_DROPBOX_TOKEN']
DROPBOX_EXPORT_FOLDER = '/jsgroup-api-test'

