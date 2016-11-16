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
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.setdefault('DEV_RDS_DB_NAME', 'theia_api'),
        'USER': os.environ.setdefault('DEV_RDS_USERNAME', 'theia'),
        'PASSWORD': os.environ.setdefault('DEV_RDS_PASSWORD', 'theia'),
        'HOST': os.environ.setdefault('RDS_HOSTNAME', '127.0.0.1'),
        'PORT': os.environ.setdefault('RDS_PORT', '5432'),
    }
}
