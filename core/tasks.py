import logging, time
from pprint import pprint, pformat

from celery import shared_task
from celery.signals import worker_ready, worker_shutdown

from dropbox_import.models import ImportFile, ImportJob, ImportJobLogEntry
from core.models import Company, FulfillmentService
from csv_parser.models import CSVRows
from dropbox_import.importers import InventoryImporter
from dropbox_import.exporters import InventoryExporter
from interfaces import ShopifyInterface, DropboxInterface


log = logging.getLogger('development')


@shared_task(bind=True)
def export_to_shopify(self, import_job_id):
    log.debug(
        'export_to_shopify(import_job_id={})'.format(import_job_id))

    # get the current import job
    job = ImportJob.objects.get(pk=import_job_id)
    log.debug('import filename: {}'.format(job.import_file.filename))
    # get the import file for this job
    file = job.import_file
    # put the company in a variable for quick access
    company = file.company
    # get the shop
    shop = ShopifyInterface(shop_url=company.shop_url)

    import_fulfillment_service = FulfillmentService.objects.get(
        is_import_destination=True,
        company=file.company,)

    # download the file
    filemeta, response = DropboxInterface().download_file(
        file.dropbox_id)

    # TODO: Capture the file format errors from CSVRows and add them to the
    # ImportJob log entries.
    rows = CSVRows(response.content,
                   file.export_type.name)
    importer = InventoryImporter(company=file.company,
                                 rows=rows)
    importer.import_data()

    # exporter = InventoryExporter(
    #     company=company,
    #     location_id=import_fulfillment_service.location_id)
    # try:
    #     exporter.export_data()
    # except Exception as e:
    #     log.exception(e)

    return True
