import os

from .common import *

###############################################################################
#                             Production Settings                             #
###############################################################################

SECRET_KEY = os.environ('DJANGO_SECRET_KEY')
DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

if 'RDS_DB_NAME' in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ['RDS_DB_NAME'],
            'USER': os.environ['RDS_USERNAME'],
            'PASSWORD': os.environ['RDS_PASSWORD'],
            'HOST': os.environ['RDS_HOSTNAME'],
            'PORT': os.environ['RDS_PORT'],
        }
    }
