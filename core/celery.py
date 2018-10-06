import os, time
from pprint import pprint, pformat
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.development')

app = Celery('core')

app.config_from_object('django.conf:settings', namespace='CELERY')

# autodiscover all the @shared_tasks in other apps' tasks.py files.
app.autodiscover_tasks()

# Testing task
# this needs to be defined here since celery won't autodiscover shared_tasks in
# files with 'test' in their filenames.
@app.task(bind=True)
def test_task(self, *args, sleep_time=30, return_value=True,
              should_raise=False, raise_early=False, **kwargs):
    print('start testing celery task')
    print(locals())

    if should_raise and raise_early:
        raise Exception('Early Testing Exception')
    time.sleep(sleep_time)
    if should_raise:
        raise Exception('Late Testing Exception')

    print('returning testing celery task')
    return return_value
