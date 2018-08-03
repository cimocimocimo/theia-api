from celery import shared_task
from celery.signals import worker_ready
import logging

log = logging.getLogger('django')

def handle_notification(data):
    """Process notification data from dropbox and start import tasks
    """
    log.debug('Controller.handle_notification called with args:')
    log.debug(data)

    # get the accounts to check for changes
    accounts = DropboxInterface.get_accounts_from_notification(data)

    log.debug('accounts: {}'.format(accounts))

    # start task process for each account
    for account in accounts:
        testing_func.delay(account)

# celery worker start signal
# setup the import script environment
@worker_ready.connect
def import_script_init(sender, **kwargs):
    log.debug('worker_ready signal')
    log.debug(sender)

    # We're only interested in the files that have changed in dropbox, not the
    # ones that are already there. So we should get a list of the existing
    # files in dropbox and store them and the dropbox file list cursor.

    # Instantiate DropboxInterface
    # dropbox_interface = DropboxInterface()

    # redis_interface = RedisInterface()

    # Check for a dropbox cursor in redis
    app_name = __package__.rsplit('.', 1)[-1]
    log.debug('app_name: ' + app_name)

    # dropbox 


@shared_task(bind=True)
def testing_func(self, account=None):
    log.debug('doing dropbox stuff')
