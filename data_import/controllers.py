import logging

from .interfaces import DropboxInterface
from .models import (Product, Variant, Color, Size,
                     ImportFile, Company, ExportType)
from .importers import ProductImporter, InventoryImporter

from celery import chain, group
from .tasks import load_import_file_meta, import_data, update_shop_inventory

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

            chain(
                load_import_file_meta.si(account),
                # import_data.s(),
                # update_shop_inventory.si()
            )()

    def get_import_files(self):
        # TODO: move the code from load_import_file_meta task to here
        raise NotImplementedError()

    def import_latest_data(self, import_filter=None):

        # import
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

        print(files_to_import)

        dropbox = DropboxInterface()

        for f in files_to_import:
            try:
                f.content = dropbox.get_file_contents(f.dropbox_id)
            except Exception as e:
                log.exception(e)
                self.retry(e)

            if f.export_type.name == ImportFile.PRODUCT:
                ProductImporter().import_data(f.content)
            elif f.export_type.name == ImportFile.INVENTORY:
                InventoryImporter().import_data(inv_text)

        return

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



    def export_data(self, companies=None):
        log.debug('Controller().export_data(companies={})'.format(companies))
        update_shop_inventory.delay(companies)
        pass

    def reset_import_files(self):
        from .models import ImportFile
        from .interfaces import DropboxInterface

        interface = DropboxInterface()

        # delete the cursor from redis
        interface.delete_account_cursors()

        # delete the import files in the database
        ImportFile.objects.all().delete()

    def full_import_export(self, companies=None):
        chain(
            get_files_to_import.si(),
            import_data.s(),
            update_shop_inventory.si()
        )()


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
