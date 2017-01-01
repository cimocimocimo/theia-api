from celery import shared_task, chain
from celery.five import monotonic
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache
from hashlib import md5
from django.conf import settings
import logging

from .importers import ProductImporter, InventoryImporter
from .exporters import ShopifyExporter
from .interfaces import DropboxInterface, ShopifyInterface
from .models import Product, Variant, ImportFile, ImportFileMeta, ImportFileMetaSet

log = logging.getLogger('django')

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

@shared_task(bind=True, default_retry_delay=60, max_retries=5, time_limit=60*10)
def load_import_file_meta(self, account=None):
    log.info('load_import_file_meta({})'.format(account))

    lock_id = get_task_lock_id(self.name, str(account))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info('get_files_to_import() already running in another job.')
            return

        dropbox_interface = DropboxInterface()

        try:
            entries = dropbox_interface.list_files(
                account=account,
                path=settings.DROPBOX_EXPORT_FOLDER)

        except Exception as e:
            log.warning(e)
            self.retry(e)

        if entries == None:
            log.warning('No data files found in dropbox folder {}.'.format(
                settings.DROPBOX_EXPORT_FOLDER))
            raise FileNotFoundError(
                'No data files found in dropbox folder {}.'.format(
                settings.DROPBOX_EXPORT_FOLDER))

        log.debug(entries)

        # create ImportFile objects for all the entries
        for e in entries:
            try:
                ImportFile.objects.get_or_create(
                    dropbox_id=e.id,
                    defaults={
                        'path_lower': e.path_lower,
                        'filename': e.name,
                        'server_modified': e.server_modified,
                    }
                )
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

@shared_task(bind=True, default_retry_delay=60, max_retries=5, time_limit=60*10)
def get_files_to_import(self, account=None):
    log.info('get_files_to_import(account={})'.format(account))

    lock_id = get_task_lock_id(self.name, str(account))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info('get_files_to_import() already running in another job.')
            return

        dropbox_interface = DropboxInterface()
        try:
            entries = dropbox_interface.list_files(
                account=account,
                path=settings.DROPBOX_EXPORT_FOLDER)

        except Exception as e:
            log.warning(e)
            self.retry(e)

        if entries == None:
            log.warning('entries was None')
            return False

        log.debug(entries)

        # This filters the FileMetaData entries to see if they are valid import
        # files and if they are creates a list of them. An instance of
        # ImportFileMetaSet is created with the list. The instance then filters the
        # files down and returns the import set with the 
        import_file_ids = ImportFileMetaSet([
                ImportFileMeta(e) for e in entries
                if ImportFileMeta.is_import_filemeta(e)
            ]).get_import_file_ids()

        log.info('get_files_to_import() returned import_file_ids: {}'
                 .format(import_file_ids))

        return import_file_ids



@shared_task(bind=True, default_retry_delay=60, max_retries=5,
             ignore_result=True, time_limit=60*60) # time limit of 1 hour
def import_data(self, company_prod_inv_ids, import_filter=None):

    # DEBUG only import Theia products for now.
    import_filter = ['Theia']

    log.info(
        'import_data(company_prod_inv_ids={}, import_filter={})'.format(
            company_prod_inv_ids, import_filter))

    if company_prod_inv_ids == False:
        return

    lock_id = get_task_lock_id(self.name, '{}-{}'.format(company_prod_inv_ids, import_filter))

    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:

            # loop over the company data, and unpack the prod and inventory ids.
            for company, (prod_id, inv_id) in company_prod_inv_ids.items():

                # if import_filter was passed then skip companies not in the import filter
                if import_filter and company not in import_filter:
                    continue

                log.info('Importing data for company: {}'.format(company))

                dropbox = DropboxInterface()

                # TODO: I think I could create tasks to download the file contents for both
                # files simultaneously. Use a chord to run the two download tasks then an
                # import task to import the two files sequentially.
                try:
                    prod_text = dropbox.get_file_contents(prod_id)
                except Exception as e:
                    log.exception(e)
                    self.retry(e)

                try:
                    inv_text = dropbox.get_file_contents(inv_id)
                except Exception as e:
                    log.exception(e)
                    self.retry(e)

                log.info('Importing Product data for company: {}'.format(company))
                try:
                    ProductImporter().import_data(prod_text)
                except Exception as e:
                    log.exception(e)
                    self.retry(e)
                else:
                    log.info('Finished Product data import for company: {}'.format(company))

                log.info('Importing Inventory data for company: {}'.format(company))
                try:
                    InventoryImporter().import_data(inv_text)
                except Exception as e:
                    log.exception(e)
                    self.retry(e)
                else:
                    log.info('Finished Inventory data import for company: {}'.format(company))

            log.info('Finished import_data()')

        else:
            log.info('import_data() already running in another job')

@shared_task(bind=True)
def update_shop_inventory(self, companies=None):
    log.info('update_shop_inventory(companies={})'.format(companies))

    lock_id = get_task_lock_id(self.name, str(companies))

    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:

            # TODO: Move this code into an exporter to clean this up.

            log.info('------- exporting inventory to shopify -------')

            exporter = ShopifyExporter()


            shopify_interface = ShopifyInterface()

            # update the products on shopify
            shop_products = shopify_interface.get_products()

            # get all the shopify products
            shopify_variants = shopify_interface.get_variants()

            for shop_variant in shopify_variants:
                log.debug(shop_variant.to_dict())

                # going to need to populate the barcodes on first run.
                # TODO: remove this once the product import is populating the store
                # with products with barcodes from the beginning
                if shop_variant.barcode == None:
                    # get the local_variant by sku
                    log.info('missing barcode for shop_varaint.sku: {}'
                             .format(shop_variant.sku))
                    # local_variant = Variant.objects.get_by_sku(shop_variant.sku)
                    # # update shop_variant with the UPC of the local_products
                    # # shopify_interface()local_variant.upc

                elif shop_variant.barcode == 'N/A':
                    log.info('Invalid barcode "{}" for shop_varaint.sku: {}'
                             .format(shop_variant.barcode, shop_variant.sku))

                else:
                    try:
                        local_variant = Variant.objects.get(upc=shop_variant.barcode)
                    except Exception as e:
                        log.warning('Could not get Variant wtih barcode: {}'
                                  .format(shop_variant.barcode))
                        log.exception(e)
                    else:
                        log.debug('local_variant={}'.format(local_variant))
                        shopify_interface.update_shop_variant_inventory(
                            shop_variant, local_variant)

            log.info('------- finished exporting inventory to shopify -------')

        else:
            log.info(
                'Shop inventory update job is already running in another worker')


