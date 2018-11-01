import logging, pytz
from pprint import pprint, pformat
from datetime import datetime, timedelta

import dropbox
from django.conf import settings
from django.utils.timezone import make_aware

from core.models import Company, FulfillmentService
from dropbox_import.models import ImportFile, ExportType, ImportJob
from interfaces import DropboxInterface, ShopifyInterface
from .tasks import export_to_shopify


log = logging.getLogger('development')
dropbox_interface = DropboxInterface()


class Controller:
    """
    Main logic for the data_importer app.
    """
    # TODO: Make the controller a singleton to allow for better communication
    # https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html

    def __init__(self):
        """Init Controller"""
        log.debug('Controller initialized')

    def startup(self):
        # TODO: Add DB log entry
        self.load_files_from_dropbox()
        pass

    def load_files_from_dropbox(self):
        # list all files in the dropbox export folder
        dropbox_files = dropbox_interface.list_all_files()
        total_numb_files = len(dropbox_files)
        # TODO: add DB log entry for number of files in dropbox

        # Delete files in DB that are not in Dropbox.
        # Create a list of dropbox file ids.
        filemeta_ids = [ filemeta.id for filemeta in dropbox_files]
        # Delete ImportFiles that don't exist in Dropbox.
        numb_deleted, numb_deleted_by_model = ImportFile.objects.exclude(
            dropbox_id__in=filemeta_ids).delete()
        # TODO: Log the number of ImportFiles deleted.

        for filemeta in dropbox_files:
            # TODO: collect the returned results
            self.process_dropbox_filemeta(filemeta)
            pass
        
    def process_dropbox_filemeta(self, filemeta):

        # TODO: return the results of the processing

        # Skip over new folders
        if type(filemeta) == dropbox.files.FolderMetadata:
            return
            
        elif type(filemeta) == dropbox.files.DeletedMetadata:
            # Remove the local ImportFile.
            ImportFile.objects.get(path_lower=filemeta.path_lower).delete()
            pass

        elif type(filemeta) == dropbox.files.FileMetadata:
            # create or update model instances

            # get the company and export type
            try:
                company_name, export_type_name = ImportFile.parse_company_export_type(
                    filemeta.name)
            except ValueError as e:
                # skip any files that don't have company and export types
                # TODO: Log this warning to the DB as well.
                log.warning(e)

            # Create the company 
            try:
                company, created = Company.objects.get_or_create(
                    name=company_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)

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
                    dropbox_id=filemeta.id,
                    defaults={
                        'path_lower': filemeta.path_lower,
                        'filename': filemeta.name,
                        'server_modified': make_aware(filemeta.server_modified, timezone=pytz.UTC),
                        'company': company,
                        'export_type': export_type,})
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
            else:
                return import_file

        return True
        
    def handle_dropbox_file_change_notification(self):
        """Lists files that have been changed in dropbox and processes them.

        This lists the changed files in Dropbox in response to the webhook
        call. New companies and export types are created. ImportFile
        instances are created and deleted as needed.

        - List the changed files
          - Check for a cursor, This is created during app initialization.
          - If no cursor then raise exception
          - Handle exception and re-init app.
            - We don't know what files were changed so we can't import them.
        - Process each file
          - Create Company, ExportType if needed.
        - Add new ImportFiles and start ImportJob in a celery task.
        - Delete old files from dropbox and their associated ImportFiles
        - Delete ImportFiles if they have been deleted on dropbox manually

        Note:  This function NEEDS to complete within 10 seconds so that the
        calling function can reply with a HTTP 200 response to Dropbox. Avoid
        extra network calls were possible. Only communicate with dropbox api.
        """

        try:
            changed_files = dropbox_interface.list_changed_files()
        except RuntimeError as e:
            # run startup to reinitialize the app
            self.startup()
            # raise to catch and log the exception further up.
            raise

        # process each changed file
        for filemeta in changed_files:
            ret_val = self.process_dropbox_filemeta(filemeta)

            # start import job for any new or edited files
            if type(filemeta) == dropbox.files.FileMetadata:
                if isinstance(ret_val, ImportFile):
                    self.start_shopify_export(ret_val.id)

    def start_shopify_export(self, import_file_id):
        """Imports Dropbox data file and then exports to Shopify.
        """

        log.debug('start_shopify_export()')
        # get the import file
        file = ImportFile.objects.get(pk=import_file_id)

        # Skip Product Exports
        if file.export_type == 'Product':
            log.debug('Skipping Product export file.')
            return

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


    # TODO: Function is unused in current app, remove later.
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

        # Get import fulfillment service for this company
        try:
            import_fulfillment_service = FulfillmentService.objects.get(company=company.id,
                                                   is_import_destination=True,)
        except FulfillmentService.DoesNotExist:
            log.error(
                'Import destination fulfillment service has not been set for {}'.format(
                    company.name))
            return

        shop = ShopifyInterface(company.shop_url,
                                import_fulfillment_service.service_id)

        shop.reset_inventory()

        # Change product_type for Theia only, this is the only company that
        # requires this for moving products between the shop and the lookbook.
        if company.name == 'Theia':
            for key, prod in shop.products.items():
                shop.update_product(prod, 'product_type', 'Theia Collection')
