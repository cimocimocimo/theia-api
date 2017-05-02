# load celery app config when core app is loaded.
from .celery import app as celery_app
