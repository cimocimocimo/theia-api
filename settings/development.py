import os

from .common import *

###############################################################################
#                             Development Settings                            #
###############################################################################

SECRET_KEY = 'this should not be used in production.'
DEBUG = True

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'theia_api',
        'USER': 'theia_api',
        'PASSWORD': 'theia_api',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
