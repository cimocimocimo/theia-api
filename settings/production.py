import os

from .common import *

###############################################################################
#                             Production Settings                             #
###############################################################################

DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    'api.theiacouture.com',
    'theia-api-production.us-east-1.elasticbeanstalk.com',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['PROD_RDS_DB_NAME'],
        'USER': os.environ['PROD_RDS_USERNAME'],
        'PASSWORD': os.environ['PROD_RDS_PASSWORD'],
        'HOST': os.environ['RDS_HOSTNAME'],
        'PORT': os.environ['RDS_PORT'],
    }
}

# Redis
REDIS_URL = os.environ.setdefault['PROD_REDIS_URL']

# Cache
CACHES['default']['LOCATION'] = REDIS_URL

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
