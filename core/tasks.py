import logging, time
from pprint import pprint, pformat

from celery import shared_task
from celery.signals import worker_ready, worker_shutdown

import db_logger
from dropbox_import.models import ImportFile, ImportJob
from core.models import Company, FulfillmentService
from csv_parser.models import CSVRows
from dropbox_import.importers import InventoryImporter
from dropbox_import.exporters import InventoryExporter
from interfaces import ShopifyInterface, DropboxInterface


log = logging.getLogger('development')
dblog = db_logger.get_logger()
dropbox_interface = DropboxInterface()


@shared_task(bind=True)
def export_to_shopify(self, import_job_id):
    log.debug(
        'export_to_shopify(import_job_id={})'.format(import_job_id))

    # get the current import job
    job = ImportJob.objects.get(pk=import_job_id)

    # get the import file for this job
    file = job.import_file
    # put the company in a variable for quick access
    company = job.import_file.company

    try:
        import_fulfillment_service = FulfillmentService.objects.get(
            is_import_destination=True,
            company=company,)
    except FulfillmentService.DoesNotExist:
        # Need a valid FulfillmentService to export inventory to
        # finish the import job and log the error
        job.finish('Import fulfillment service not set.', err=True)
        return

    log.debug('import filename: {}'.format(job.import_file.filename))

    # get the shop
    shop = ShopifyInterface(
        shop_url=company.shop_url,
        fulfillment_service_id=import_fulfillment_service.service_id)

    # download the file
    filemeta, response = dropbox_interface.download_file(
        file.dropbox_id)

    # TODO: Capture the file format errors from CSVRows and add them to the
    # ImportJob log entries.
    rows = CSVRows(response.content,
                   file.export_type.name)
    importer = InventoryImporter(company=company,
                                 rows=rows)
    importer.import_data()

    exporter = InventoryExporter(
        company=company,
        fulfillment_service_id=import_fulfillment_service.service_id)
    try:
        exporter.export_data()
    except Exception as e:
        log.exception(e)

    return True
