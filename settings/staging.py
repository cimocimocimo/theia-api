import os

from .common import *

###############################################################################
#                               Staging Settings                              #
###############################################################################

DEBUG = True

ALLOWED_HOSTS = [
    'api.staging.theiacouture.com',
    'theia-api-staging.us-east-1.elasticbeanstalk.com',]

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['STAGE_RDS_DB_NAME'],
        'USER': os.environ['STAGE_RDS_USERNAME'],
        'PASSWORD': os.environ['STAGE_RDS_PASSWORD'],
        'HOST': os.environ['RDS_HOSTNAME'],
        'PORT': os.environ['RDS_PORT'],
    }
}
