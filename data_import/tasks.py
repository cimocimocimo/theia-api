from celery import shared_task, chain
from celery.five import monotonic
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache
from hashlib import md5
from django.conf import settings
import logging, re

from time import sleep

from .importers import ProductImporter, InventoryImporter
from .interfaces import DropboxInterface, ShopifyInterface
from .models import Product, Variant

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
def get_files_to_import(self, account=None):
    log.debug('get_files_to_import(account={})'.format(account))

    lock_id = get_task_lock_id(self.name, str(account))

    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:

            dropbox_interface = DropboxInterface()
            try:
                entries = dropbox_interface.list_files(
                    account=account,
                    path=settings.DROPBOX_EXPORT_FOLDER)

            except Exception as e:
                log.warning(e)
                self.retry(e)

            else:
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

                log.debug(import_file_ids)

                return import_file_ids
        else:
            log.debug('get_files_to_import() already running in another job.')

@shared_task(bind=True, default_retry_delay=60, max_retries=5,
             ignore_result=True, time_limit=60*30)
def import_data(self, company_prod_inv_ids, import_filter=None):

    log.debug(
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

                log.debug('Importing data for company: {}'.format(company))

                dropbox = DropboxInterface()

                # TODO: I think I could create tasks to download the file contents for both
                # files simultaneously. Use a chord to run the two download tasks then an
                # import task to import the two files sequentially.
                try:
                    prod_text = dropbox.get_file_contents(prod_id)
                except Exception as e:
                    log.debug(e)
                    self.retry(e)

                try:
                    inv_text = dropbox.get_file_contents(inv_id)
                except Exception as e:
                    log.debug(e)
                    self.retry(e)

                log.debug('Importing Product data for company: {}'.format(company))
                try:
                    ProductImporter().import_data(prod_text)
                except Exception as e:
                    log.debug(e)
                    self.retry(e)
                else:
                    log.debug('Finished Product data import for company: {}'.format(company))

                log.debug('Importing Inventory data for company: {}'.format(company))
                try:
                    InventoryImporter().import_data(inv_text)
                except Exception as e:
                    log.debug(e)
                    self.retry(e)
                else:
                    log.debug('Finished Inventory data import for company: {}'.format(company))

            log.debug('Finished import_data()')

        else:
            log.debug('import_data() already running in another job')

@shared_task(bind=True)
def update_shop_inventory(self, companies=None):
    log.debug('update_shop_inventory(companies={})'.format(companies))

    lock_id = get_task_lock_id(self.name, str(companies))

    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:

            # TODO: Move this code into an exporter to clean this up.

            log.debug('------- exporting inventory to shopify -------')

            shopify_interface = ShopifyInterface()
            # update the products on shopify

            # get all the shopify products
            shopify_products = shopify_interface.get_products()

            for shop_product in shopify_products:
                log.debug(shop_product.handle)

                for shop_variant in shop_product.variants:
                    log.debug(shop_variant.title)
                    log.debug(shop_variant.to_dict())

                    # going to need to populate the barcodes on first run.
                    # TODO: remove this once the product import is populating the store
                    # with products with barcodes from the beginning
                    if shop_variant.barcode == None:
                        # get the local_variant by sku
                        log.debug(shop_variant.sku)
                        # local_variant = Variant.objects.get_by_sku(shop_variant.sku)
                        # # update shop_variant with the UPC of the local_products
                        # # shopify_interface()local_variant.upc
                    else:
                        shopify_interface.update_shop_variant_inventory(shop_variant)

            log.debug('------- finished exporting inventory to shopify -------')

        else:
            log.debug(
                'Shop inventory update job is already running in another worker')


class ImportFileMeta:
    type_company_regex = r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$'
    type_company_pattern = re.compile(type_company_regex)

    def __init__(self, filemeta):
        if not self.is_import_filemeta(filemeta):
            raise Exception(
                'Invalid FileMetaData passed to ImportFileMetaconstructor')
        self.filemeta = filemeta
        self.export_type, self.company = self._get_type_company_from_filename(
            filemeta.name)

    def _get_type_company_from_filename(self, filename):
        match = self.type_company_pattern.match(filename)
        if match:
            return match.group(1,2)
        else:
            return None

    @property
    def id(self):
        return self.filemeta.id

    @classmethod
    def is_import_filemeta(cls, filemeta):
        """
        Tests a FileMetaData instance to see if it is a valid Import file.
        """
        return (cls.type_company_pattern.match(filemeta.name) and
                filemeta.path_lower.startswith(
                    settings.DROPBOX_EXPORT_FOLDER))

class ImportFileMetaSet:
    # Export type keys
    PRODUCT = 'Product'
    INVENTORY = 'Inventory'

    def __init__(self, import_files):
        self.files = import_files
        self.company_set = set(
            f.company for f in self.files)
        self.export_type_set = set(
            f.export_type for f in self.files)

    def get_filtered_by_company_type(self, company, export_type):
        return [
            f for f in self.files
            if f.company == company and
            f.export_type == export_type
        ]

    def get_most_recent_file_from_list(self, file_list):
        if len(file_list):
            # sort by server modified time, newest first
            file_list.sort(key=lambda x: x.filemeta.server_modified,
                            reverse=True)
            return file_list[0]
        else:
            return None

    def get_prod_inv_ids_by_company(self, company):
        prod = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.PRODUCT))

        inv = self.get_most_recent_file_from_list(
            self.get_filtered_by_company_type(company, self.INVENTORY))

        return (prod.id, inv.id)

    def get_import_file_ids(self):
        """get the import files by company"""

        if len(self.files):
            return {
                company: self.get_prod_inv_ids_by_company(company)
                for company in self.company_set
            }
        else:
            return False

