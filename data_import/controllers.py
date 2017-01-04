import logging
from celery import chain, group

from .interfaces import DropboxInterface
from .tasks import get_files_to_import, import_data, update_shop_inventory

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
            chain(
                get_files_to_import.si(account),
                import_data.s(),
                update_shop_inventory.si()
            )()

    def get_import_files(self):
        # TODO: move the code from load_import_file_meta task to here
        raise NotImplementedError()


    def import_latest_data(self, companies=None):
        chain(
            get_files_to_import.s(None),
            import_data.s(import_filter=companies),
        )()

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
