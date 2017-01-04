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
from .models import Product, Variant, Company, ExportType, ImportFile, ImportFileMeta, ImportFileMetaSet

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
            log.info('load_import_file_meta() already running in another job.')
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

        log.debug('Number of added entries: {}\nNumber of deleted entries: {}'
                  .format(len(entries['added']), len(entries['deleted'])))

        log.debug('Added entries:')
        for e in entries['added']:
            log.debug('name: {}, modified: {}, id: {}'
                      .format(e.name, e.server_modified, e.id))
        log.debug('Deleted entries:')
        for e in entries['deleted']:
            log.debug('name: {}'
                      .format(e.name))

        # create ImportFile objects for all the entries
        for e in entries['added']:
            # get the company and export type
            try:
                company_name, export_type_name = ImportFile.parse_company_export_type(e.name)
            except ValueError as e:
                log.warning(e)
                continue

            try:
                company, created = Company.objects.get_or_create(
                    name=company_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                export_type, created = ExportType.objects.get_or_create(
                    name=export_type_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                import_file, created = ImportFile.objects.update_or_create(
                    dropbox_id=e.id,
                    defaults={
                        'path_lower': e.path_lower,
                        'filename': e.name,
                        'server_modified': e.server_modified,
                        'company': company,
                        'export_type': export_type,
                    }
                )
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

        # remove the deleted objects
        for e in entries['deleted']:
            try:
                ImportFile.objects.filter(path_lower=e.path_lower).delete()
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return


@shared_task(bind=True, default_retry_delay=60, max_retries=5,
             ignore_result=True, time_limit=60*60) # time limit of 1 hour
def import_data(self, import_filter):

    # DEBUG only import Theia products for now.
    import_filter = ['Theia']

    log.info(
        'import_data(import_filter={})'.format(import_filter))

    lock_id = get_task_lock_id(self.name, '{}-{}'.format(company_prod_inv_ids, import_filter))

    with task_lock(lock_id, self.app.oid) as acquired:
        if not acquired:
            log.info('import_data() already running in another job')
            return

        Controller().import_latest_data(import_filter)

    log.info('Finished import_data()')


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


