from celery import shared_task, chain, group
from celery.five import monotonic
from contextlib import contextmanager
from django.core.cache import cache
from hashlib import md5
from django.conf import settings
import logging

from .controllers import Controller

from .importers import ProductImporter, InventoryImporter
from .interfaces import DropboxInterface, ShopifyInterface
from .models import Product, Variant, Company, ExportType, ImportFile

log = logging.getLogger(__name__).getChild('celery')

LOCK_EXPIRE = 60 * 10 # Lock expires in 10 minutes

@contextmanager
def task_lock(lock_id, oid):
    log.debug('Getting lock: lock_id: {}, oid: {}'.format(lock_id, oid))

    timeout_at = monotonic() + LOCK_EXPIRE - 3
    status = cache.add(lock_id, oid, LOCK_EXPIRE)

    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if monotonic() < timeout_at:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else.
            log.debug('Releasing lock_id: {}'.format(lock_id))
            cache.delete(lock_id)

def get_task_lock_id(task_name, task_sig):
    """
    Get a formatted lock id string.

    task_name: name of the task
    task_sig: unique string built from the task arguments, should be identical
    for each set of arguments to the task.
    """
    task_hexdigest = md5(task_sig.encode('utf-8')).hexdigest()
    return '{0}-lock-{1}'.format(task_name, task_hexdigest)


def handle_notification(data):
    """Process notification data from dropbox and start import tasks
    """
    log.debug('Controller.handle_notification called with args:')
    log.debug(data)

    # get the accounts to check for changes
    accounts = DropboxInterface.get_accounts_from_notification(data)

    log.debug('accounts: {}'.format(accounts))

    # TODO: We are working with a single Dropbox account so we should remove this later
    # start task process for each account
    for account in accounts:
        full_import_export_task.delay(account)
        # spawn_full_import_job(account)

def spawn_full_import_job(account=None):
    chain(
        load_import_file_meta.si(account),
        import_data.si(),
        update_shop_inventory.si()
    )()

@shared_task(bind=True, default_retry_delay=60, max_retries=5, time_limit=60*10)
def load_import_file_meta(self, account=None):
    log.info('load_import_file_meta({})'.format(account))

    lock_id = get_task_lock_id(self.name, str(account))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info('load_import_file_meta() already running in another job.')
            return

        Controller().load_import_files(account)

@shared_task(bind=True, default_retry_delay=60, max_retries=5,
             ignore_result=True, time_limit=60*60) # time limit of 1 hour
def import_data(self, import_filter=None):

    # DEBUG only import Theia products for now.
    import_filter = ['Theia']

    log.info(
        'import_data(import_filter={})'.format(import_filter))

    lock_id = get_task_lock_id(self.name, '{}'.format(import_filter))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info('import_data() already running in another job')
            return

        c = Controller()
        try:
            c.import_latest_data(import_filter)
        except Exception as e:
            log.exception(e)
            self.retry(e)

    log.info('Finished import_data()')

@shared_task(bind=True)
def update_shop_inventory(self, companies=None):
    log.info('update_shop_inventory(companies={})'.format(companies))

    lock_id = get_task_lock_id(self.name, str(companies))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info(
                'Shop inventory update job is already running in another worker')
            return

        Controller().update_shop_inventory()

    log.info('Finished update_shop_inventory()')

@shared_task(bind=True, default_retry_delay=60, max_retries=5,
             ignore_result=True, time_limit=60*60) # time limit of 1 hour
def full_import_export_task(self, account=None, companies=None):

    c = Controller()
    try:
        c.full_import_export(account, import_filter=['Theia'])
    except Exception as e:
        log.exception(e)
        self.retry(e)

    # lock_id = get_task_lock_id(self.name, '{}-{}'.format(account, companies))

    # with task_lock(lock_id, self.app.oid) as acquired:
    #     if not acquired:
    #         log.info('full_import_export_task() already running in another job')
    #         return

    #     c = Controller()
    #     try:
    #         c.full_import_export(account, companies)
    #     except Exception as e:
    #         log.exception(e)
    #         self.retry(e)

    log.info('Finished full_import_export()')
