"""
Django settings for api project.

Generated by 'django-admin startproject' using Django 1.10.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

ADMINS = [('Aaron', 'aaron@cimolini.com')]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd Party Apps
    'django_extensions',

    # Local Apps
    'core.apps.CoreConfig',
    'webhook.apps.WebhookConfig',
    'data_import.apps.DataImportConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Logging
MAX_LOG_SIZE = 1024*1000*5 # 5MB in bytes
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'data_import': {
            'handlers': ['general'],
            'level': 'INFO',
            'propagate': True,
        },
        'data_import.import': {
            'handlers': ['import'],
            'level': 'INFO',
            'propagate': True,
        },
        'data_import.export': {
            'handlers': ['export'],
            'level': 'INFO',
            'propagate': True,
        },
        'data_import.interface': {
            'handlers': ['interface'],
            'level': 'INFO',
            'propagate': True,
        },
        'data_import.celery': {
            'handlers': ['celery'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'handlers': {
        'general': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': '/opt/python/log/data_import.log',
            'formatter': 'normal',
            'maxBytes': MAX_LOG_SIZE,
            'backupCount': 5,
        },
        'import': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': '/opt/python/log/data_import_import.log',
            'formatter': 'normal',
            'maxBytes': MAX_LOG_SIZE,
            'backupCount': 5,
        },
        'export': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': '/opt/python/log/data_import_export.log',
            'formatter': 'normal',
            'maxBytes': MAX_LOG_SIZE,
            'backupCount': 5,
        },
        'interface': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': '/opt/python/log/data_import_interface.log',
            'formatter': 'normal',
            'maxBytes': MAX_LOG_SIZE,
            'backupCount': 5,
        },
        'celery': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': '/opt/python/log/data_import_celery.log',
            'formatter': 'normal',
            'maxBytes': MAX_LOG_SIZE,
            'backupCount': 5,
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d\n%(message)s'
        },
        'normal': {
            'format': '%(levelname)s %(asctime)s\n%(message)s'
        },
    },
}

# Redis
REDIS_PROTOCOL = 'redis://'
REDIS_DOMAIN = 'theia-api-dev.iby5d3.0001.use1.cache.amazonaws.com'
REDIS_PORT = 6379

# Dropbox settings
DROPBOX_APP_KEY = os.environ['DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['DROPBOX_APP_SECRET']
DROPBOX_TOKEN = os.environ['DROPBOX_TOKEN']
DROPBOX_EXPORT_FOLDER = os.environ.setdefault('DROPBOX_EXPORT_FOLDER', '/e-commerce')

# Celery
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Montreal'

# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
