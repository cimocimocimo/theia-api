import sys, logging, dropbox

from django.conf import settings
from pprint import pprint, pformat
from datetime import datetime, timedelta

from core.models import Company
from core.interfaces import DropboxInterface, ShopifyInterface

from dropbox_import.importers import InventoryImporter
from dropbox_import.exporters import InventoryExporter

log = logging.getLogger('django')

class Controller:
    """
    Main logic for the data_importer app.
    """

    def __init__(self):
        """Init Controller"""
        log.debug('Controller initialized')
        self.dropbox_interface = DropboxInterface()

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

        shopify = ShopifyInterface(company)
        products = shopify.get_products()
        for p in products:
            save_needed = False

            # only update collection for Theia
            if company.name == 'Theia':
                if p.product_type == 'Theia Shop':
                    p.product_type = 'Theia Collection'
                    save_needed = True

            for v in p.variants:
                if v.inventory_quantity:
                    save_needed = True
                    v.inventory_quantity = 0

            if save_needed:
                print('saving product: {}'.format(p.title))
                print(p.save())
