import logging, dropbox
from pprint import pprint, pformat
from datetime import datetime, timedelta

from django.conf import settings

from core.models import Company, FulfillmentService
from dropbox_import.models import (ImportFile, ExportType, ImportJob,
                                   ImportJobLogEntry)
from dropbox_import.db_logger import DBLogger
from interfaces import DropboxInterface, ShopifyInterface
from .tasks import export_to_shopify


log = logging.getLogger('development')
dropbox_interface = DropboxInterface()


class Controller:
    """
    Main logic for the data_importer app.
    """

    def __init__(self):
        """Init Controller"""
        log.debug('Controller initialized')

    def start_shopify_export(self, import_file_id):
        """Imports Dropbox data file and then exports to Shopify.
        """
        log.debug('start_shopify_export()')
        # get the import file
        file = ImportFile.objects.get(pk=import_file_id)
        # Create an ImportJob for this file
        job = ImportJob.objects.create(import_file=file)
        # try to start celery task
        try:
            job.start(job_task=export_to_shopify)
        except Exception as e:
            # There was an error starting the celery task
            raise

        return 'Export job started successfully or company "{}"'.format(
            file.company)

    def get_import_data(self):
        """Fetch import files from dropbox

        This is a new function and is not currently being used. Should replace
        load_import_files() when ready.
        """
        entries = self.dropbox_interface.list_files(
            settings.DROPBOX_EXPORT_FOLDER)

        # get current datetime
        now = datetime.now()
        expiry_date = now + timedelta(-7)
        recent_files = []
        import_metadata = {}

        for e in entries:
            # skip non-files
            if type(e) != dropbox.files.FileMetadata:
                continue

            # delete files older than 2 weeks
            if e.server_modified < expiry_date:
                self.dropbox_interface.delete_file(e.path_lower)

            else:
                recent_files.append(e)


        # sort the recent files by company then by filetype
        # only save the most recent file of each
        for e in recent_files:
            # parse the filename for company and export type
            c, t = self.dropbox_interface.parse_company_export_type(e.name)

            # create the company and type keys if they don't exist
            if c not in import_metadata:
                # initialize the keys and save the entry
                import_metadata[c] = {t: e}
                # first time this key has been seen
                continue

            if t not in import_metadata[c]:
                # initialize the keys and save the entry
                import_metadata[c][t] = e
                # first time this key has been seen
                continue

            # check for a file in the import_metadata spot already
            if import_metadata[c][t].server_modified < e.server_modified:
                import_metadata[c][t] = e


        for c, _type in import_metadata.items():
            pprint(c)
            for t, e in _type.items():
                pprint(t)
                pprint(e.name)
                pprint(str(e.server_modified))

        # pprint(import_metadata)
        # get the last 2 weeks of file metadata
        # delete files on dropbox older than a month

    def _get_companies_or_none(self, names=None):
        if names:
            try:
                companies = Company.objects.filter(name__in=names)
            except Exception as e:
                log.exception(e)
                raise
        else:
            companies = Company.objects.all()

        if len(companies):
            return companies
        else:
            return None

    def update_shop_inventory(self, company_name=None):
        try:
            companies = self._get_companies_or_none(company_name)
        except:
            raise

        # loop over all the companies in the database
        for c in companies:
            # create an Exporter for each company.
            if not c.has_shop_url:
                continue

            if not c.should_import:
                continue

            exporter = InventoryExporter(c)
            exporter.export_data()

    def reset_inventory(self, company):
        if not company.has_shop_url:
            return

        shop = ShopifyInterface(company)

        # Get import fulfillment service for this company
        try:
            import_fulfillment_service = FulfillmentService.objects.get(company=company.id,
                                                   is_import_destination=True,)
        except FulfillmentService.DoesNotExist:
            log.error(
                'Import destination fulfillment service has not been set for {}'.format(
                    company.name))
            return

        shop.reset_inventory()

        # Change product_type for Theia only, this is the only company that
        # requires this for moving products between the shop and the lookbook.
        if company.name == 'Theia':
            for key, prod in shop.products.items():
                shop.update_product(key, 'product_type', 'Theia Collection')
