import os

from .common import *

###############################################################################
#                               Staging Settings                              #
###############################################################################

DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'api.staging.theiacouture.com',
    'jsgroup-api-prod.rku9famy7u.us-east-1.elasticbeanstalk.com',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['STAGE_RDS_DB_NAME'],
        'USER': os.environ['STAGE_RDS_USERNAME'],
        'PASSWORD': os.environ['STAGE_RDS_PASSWORD'],
        'HOST': os.environ['RDS_HOSTNAME'],
        'PORT': os.environ['RDS_PORT'],
    }
}

# Redis
REDIS_DB = os.environ['STAGE_REDIS_DB']
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
DROPBOX_APP_KEY = os.environ['STAGE_DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['STAGE_DROPBOX_APP_SECRET']
DROPBOX_TOKEN = os.environ['STAGE_DROPBOX_TOKEN']
DROPBOX_EXPORT_FOLDER = '/JSGroup-Testing'
