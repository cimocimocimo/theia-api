import os

from .common import *

###############################################################################
#                             Development Settings                            #
###############################################################################

DEBUG = True

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DEV_RDS_DB_NAME'],
        'USER': os.environ['DEV_RDS_USERNAME'],
        'PASSWORD': os.environ['DEV_RDS_PASSWORD'],
        'HOST': os.environ['RDS_HOSTNAME'],
        'PORT': os.environ['RDS_PORT'],
    }
}
