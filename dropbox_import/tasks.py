from celery import shared_task
from celery.signals import worker_ready, worker_shutdown
import logging, sys
from pprint import pprint, pformat
from csv_parser.models import CSVRows

log = logging.getLogger('django')

from core.interfaces import DropboxInterface
from core.models import Company
from .importers import InventoryImporter
# from .exporters import InventoryExporter

@shared_task(bind=True)
def handle_notification(self, data):
    """Process notification data from dropbox and start import tasks
    """

    log.debug('handle_notification task')

    # Get the changed files that triggered the webhook.
    files_to_import = DropboxInterface().get_new_import_files(data)

    log.debug(pformat(files_to_import))

    # Create a company entry in the DB if it doesn't exist.
    # This is handy to create an entry
    for file in files_to_import:
        try:
            company, created = Company.objects.get_or_create(
                name=file['company'])
        except ValueError as e:
            log.warning(e)
        except Exception as e:
            # Something bad happened, log and return.
            # TODO: Send exception to admins via email
            log.exception(e)
            log.error(
                'Could not get or create Company with name "{}" from db'
                .format(file['company']))
            return

    # Process each inventory file in subtask, skip product data for now.
    [ process_inventory_file.delay(f)
      for f in files_to_import
      if f['export_type'] == 'Inventory' ]

@shared_task(bind=True)
def process_inventory_file(self, import_file):
    log.debug('Calling process_inventory_file task')
    log.debug(pformat(import_file))

    # download the file
    dropbox_interface = DropboxInterface()
    filemeta, response = dropbox_interface.download_file(import_file['id'])

    log.debug(pformat(filemeta))
    log.debug(response)

    # Get the company object for this import file
    try:
        company = Company.objects.get(name=import_file['company'])
    except Exception as e:
        log.warning(e)
        log.warning(
            'Company object with name "{}" not found in database'
            .format(import_file['company']))

    importer = InventoryImporter(
        company=company,
        rows=CSVRows(
            response.content,
            import_file['export_type']))
    importer.import_data()

    # exporter = InventoryExporter(company=import_file['company'])


# celery worker start signal
# setup the import script environment
@worker_ready.connect
def import_script_startup(sender, **kwargs):
    log.debug('worker_ready signal')
    log.debug(sender)

    # We're only interested in the files that have changed in dropbox, not the
    # ones that are already there. So we should get a list of the existing
    # files in dropbox and store them and the dropbox file list cursor.

    # Instantiate DropboxInterface
    dropbox_interface = DropboxInterface()

    # redis_interface = RedisInterface()

    # Check for a dropbox cursor in redis
    app_name = __package__.rsplit('.', 1)[-1]
    log.debug('app_name: ' + app_name)

    dropbox_interface.startup()

    # dropbox 

@worker_shutdown.connect
def import_script_shutdown(**kwargs):
    pass
    log.debug('worker_shutting_down signal')

    dropbox_interface = DropboxInterface()
    dropbox_interface.shutdown()