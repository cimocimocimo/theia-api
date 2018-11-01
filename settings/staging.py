import os

from .common import *

###############################################################################
#                               Staging Settings                              #
###############################################################################

DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'api.staging.theiacouture.com',
    'jsgroup-api-stage.us-east-1.elasticbeanstalk.com',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'api_staging',
        'USER': 'api_staging',
        'PASSWORD': os.environ['STAGE_RDS_PASSWORD'],
        'HOST': RDS_HOSTNAME,
        'PORT': RDS_PORT,
    }
}

# Redis
REDIS_DB = 1
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
# Using Production data for staging
DROPBOX_APP_KEY = os.environ['PROD_DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['PROD_DROPBOX_APP_SECRET']
DROPBOX_TOKEN = os.environ['PROD_DROPBOX_TOKEN']
DROPBOX_EXPORT_FOLDER = '/e-commerce'
