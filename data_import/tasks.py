from celery import shared_task
import logging

from .controllers import Controller

from .importers import ProductImporter, InventoryImporter
from .interfaces import DropboxInterface, ShopifyInterface, RedisInterface
from .models import Product, Variant, Company, ExportType, ImportFile

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


@shared_task(bind=True)
def testing_func(self, account=None):
    log.debug('doing dropbox stuff')



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
        c.full_import_export(account)
    except Exception as e:
        log.exception(e)
        self.retry(e)

    log.info('Finished full_import_export()')
