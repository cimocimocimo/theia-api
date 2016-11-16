import os

from .common import *

###############################################################################
#                             Production Settings                             #
###############################################################################

DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

if 'RDS_DB_NAME' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['PROD_RDS_DB_NAME'],
            'USER': os.environ['PROD_RDS_USERNAME'],
            'PASSWORD': os.environ['PROD_RDS_PASSWORD'],
            'HOST': os.environ['RDS_HOSTNAME'],
            'PORT': os.environ['RDS_PORT'],
        }
    }
