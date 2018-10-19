import logging
from pprint import pprint, pformat

from celery import shared_task
from celery.signals import worker_ready, worker_shutdown

from csv_parser.models import CSVRows
from interfaces import DropboxInterface, ShopifyInterface
from core.models import Company, Inventory, FulfillmentService
from .importers import InventoryImporter
from .exporters import InventoryExporter
from core.controllers import Controller


log = logging.getLogger('development')
controller = Controller()


@shared_task(bind=True)
def process_inventory_file(self, import_file):
    log.debug('Calling process_inventory_file task')
    log.debug(pformat(import_file))

    # Get or create the company object for this import file
    try:
        company, created = Company.objects.get_or_create(
            name=import_file['company'])

    except Exception as e:
        # TODO: Send exception to admins via email
        log.exception(e)
        log.error(
            'Could not get or create Company with name "{}" from db'
            .format(import_file['company']))
        return

    # Log and return if we shouldn't import this file or are missing the
    # Shopify API url.
    if not company.should_import and not company.has_shop_url:
        log.info(
            'Skipping {} file for Company {}.'
            .format(
                import_file['export_type'], import_file['company']))
        return

    # get the fulfillment service that has been set as the destination
    try:
        import_fulfillment_service = FulfillmentService.objects.get(
            is_import_destination=True,
            company=company,)
    except FulfillmentService.DoesNotExist:
        # return if no fulfillment service has been set as the default
        log.error(
            'No import destination has been set for company: {}'
            .format(company.name))
        return

    shop = ShopifyInterface(company.shop_url, import_fulfillment_service.id)

    # download the file
    dropbox_interface = DropboxInterface()
    filemeta, response = dropbox_interface.download_file(import_file['id'])

    # Create importer instance with the csv file data and company. Then import
    # the data into Redis.
    importer = InventoryImporter(
        company=company,
        rows=CSVRows(
            response.content,
            import_file['export_type']))
    importer.import_data()

    exporter = InventoryExporter(company=company,
                                 location_id=import_fulfillment_service.location_id)
    try:
        exporter.export_data()
    except Exception as e:
        log.exception(e)


# celery worker start signal
# setup the import script environment
@worker_ready.connect
def import_script_startup(sender, **kwargs):
    log.debug('worker_ready signal')
    log.debug(sender)

    controller.startup()


@worker_shutdown.connect
def import_script_shutdown(**kwargs):
    pass
    log.debug('worker_shutting_down signal')

    dropbox_interface = DropboxInterface()
    # Deletes the cursor in Redis.
    dropbox_interface.shutdown()

    # Reset Inventory in Redis for all companies
    # get all companies
    companies = Company.objects.all()
    for c in companies:
        Inventory(c.name).reset()
