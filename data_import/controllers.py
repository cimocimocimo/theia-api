import logging
from django.conf import settings

from .interfaces import DropboxInterface, ShopifyInterface, RedisInterface
from .models import (Product, Variant, Color, Size,
                     ImportFile, Company, ExportType)
from .importers import ProductImporter, InventoryImporter
from .exporters import InventoryExporter

# TODO: Remove all celery task code from Controller
# from celery import chain, group
# from .tasks import load_import_file_meta, import_data, update_shop_inventory

log = logging.getLogger('django')

class Controller:
    """
    Main logic for the data_importer app.
    """

    def __init__(self):
        """Init Controller"""
        log.debug('Controller initialized:')
        log.debug(self)

    def load_import_files(self, account=None):

        # TODO: Refactor this mess.
        dropbox_interface = DropboxInterface()

        entries = dropbox_interface.list_files(settings.DROPBOX_EXPORT_FOLDER,
                                               account)

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
                # skip any files that don't have company and export types
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

        # scan the import files and mark expired files
        # TODO: Add some way to mark the older import files as expired.

    def import_latest_data(self, import_filter=None):
        """ Import most recent, unimported files """

        # get the latest import files for each of companies
        files_to_import = [
            c.importfile_set.filter(
                export_type=t,
                import_status=ImportFile.NOT_IMPORTED
            ).latest()
            for t in ExportType.objects.all()
            for c in Company.objects.all()]

        importers = {
            ImportFile.PRODUCT: ProductImporter(),
            ImportFile.INVENTORY: InventoryImporter()}

        for f in files_to_import:
            if import_filter and f.company.name not in import_filter:
                continue
            else:
                importers[f.export_type.name].import_data(f)

    def reset_local_products(self):
        # removes all the products and their variants in the database
        for c in [Product, Variant, Size, Color]:
            c.objects.all().delete()

        # remove Inventory data from redis
        redis = RedisInterface()
        for k in redis.client.scan_iter('*inventory*'):
            redis.client.delete(k)
        for k in redis.client.scan_iter('*variant*'):
            redis.client.delete(k)

    def export_data(self, companies=None):
        log.debug('Controller().export_data(companies={})'.format(companies))
        update_shop_inventory.delay(companies)
        pass

    def reset_import_files(self):
        """reset import_file db tables and redis keys"""

        from .models import ImportFile
        from .interfaces import DropboxInterface, RedisInterface

        dropbox = DropboxInterface()
        redis = RedisInterface()

        # delete the cursor from redis
        dropbox.delete_account_cursors()

        # get import files with redis keys and delete one by one to ensure
        # their delete() methods are called.
        for f in ImportFile.objects.exclude(redis_key__isnull=True):
            f.delete()

        # cleanup any left over redis keys
        # TODO: get this key from the redis client or ImportFile model somehow
        for k in redis.client.keys('import_file:*'):
            redis.client.delete(k)

        # bulk delete the rest of the import files in the database.
        # ImportFile.delete() is NOT called in this case.
        ImportFile.objects.all().delete()

    def import_shop_data(self):
        # get all the products from the shopify store
        shopify = ShopifyInterface()
        redis = RedisInterface()
        products = shopify.get_products()
        for p in products:
            # TODO: Store the product dict in redis
            # p.to_dict()
            pass

    def update_shop_inventory(self):
        exporter = InventoryExporter()
        exporter.export_data()

    def reset_shop_inventory(self):
        shopify = ShopifyInterface()
        products = shopify.get_products()
        for p in products:
            save_needed = False
            if p.product_type == 'Theia Shop':
                p.product_type = 'Theia Collection'
                update_needed = True
            for v in p.variants:
                if v.inventory_quantity:
                    save_needed = True
                    v.inventory_quantity = 0
                if v.barcode:
                    save_needed = True
                    v.barcode = ''
            if save_needed:
                print('saving product: {}'.format(p.title))
                print(p.save())
            else:
                print('skipping')

    def full_import_export(self, account=None, import_filter=None):
        self.load_import_files(account)
        self.import_latest_data(import_filter)
        self.update_shop_inventory()
