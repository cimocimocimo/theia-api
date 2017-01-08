import logging
from django.conf import settings

from .interfaces import DropboxInterface
from .models import (Product, Variant, Color, Size,
                     ImportFile, Company, ExportType)
from .importers import ProductImporter, InventoryImporter

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

    def handle_notification(self, data):
        log.debug('Controller.handle_notification called with args:')
        log.debug(data)

        # get the accounts to check for changes
        accounts = DropboxInterface.get_accounts_from_notification(data)

        log.debug('accounts: {}'.format(accounts))

        # start task process for each account
        for account in accounts:

            # keep a cache of all the dropbox files in redis
            # organized by company and then by export type
            # keep the most recent company inventory and product file in redis
            # handle each file separately.

            # store all the files
            # for each file that comes in
            # get it's export_type and company from the filename
            # also get the server modified date and the dropbox file id

            # chain(
            #     load_import_file_meta.si(account),
            #     # import_data.s(),
            #     # update_shop_inventory.si()
            # )()
            pass

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

    def import_latest_data(self, import_filter=None):
        """ import most recent, unimported files """
        # get the latest import files for each of companies
        companies = Company.objects.all()
        export_types = ExportType.objects.all()

        latest_import_files = [
            c.importfile_set.filter(export_type=t).latest()
            for t in export_types for c in companies
        ]

        files_to_import = [
            f for f in latest_import_files
            if f.import_status == ImportFile.NOT_IMPORTED
        ]

        importers = {
            ImportFile.PRODUCT: ProductImporter(),
            ImportFile.INVENTORY: InventoryImporter(),
        }

        for f in files_to_import:
            importers[f.export_type.name].import_data(f)

    def reset_local_products(self):
        # removes all the products and their variants in the database
        for c in [Product, Variant, Size, Color]:
            c.objects.all().delete()
        

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
        for k in redis.client.keys('data_import:import_file:*'):
            redis.client.delete(k)

        # bulk delete the rest of the import files in the database.
        # ImportFile.delete() is NOT called in this case.
        ImportFile.objects.all().delete()

    def full_import_export(self, companies=None):
        # chain(
        #     get_files_to_import.si(),
        #     import_data.s(),
        #     update_shop_inventory.si()
        # )()
        pass


    """
    Import process

    webhook notification

    for each account start an import task

    load the files that have changed
    - get the dropbox cursor for that account
    - get the updated files if we have a valid cursor
    - else get all files
    - save the dropbox cursor

    sort files by company then by export type

    take the latest file of each

    start a new task for each company
    - import the products then the inventory
    - then run the export to shopify for that company



    """
