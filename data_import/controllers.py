import logging
from celery import chain, group

from .interfaces import DropboxInterface
from .tasks import get_files_to_import

log = logging.getLogger('django')

class Controller:
    """
    Main logic for the data_importer app.
    """

    def __init__(self):
        """Init Controller"""
        log = logging.getLogger('django')
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
            get_files_to_import.delay(account)

    def get_import_file_set(self, cursor, account):
        dropbox_interface = DropboxInterface()

        # get the 
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
