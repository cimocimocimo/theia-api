"""
Initial import should get all the files from dropbox

subsequent requests should only get the changed files

keep a cache of the last imported files - why?

run the Product imports first, then run the inventory imports

how do the shopify products start to fit in with all this?

need to get a list of all the product ids 
"""

from celery import shared_task, chain

from django.conf import settings
import logging, dropbox, redis, json, re, csv
from .importers import ProductImporter, InventoryImporter
from .interfaces import DropboxInterface, ShopifyInterface
from .models import Product, Variant

log = logging.getLogger('django')

@shared_task
def import_product_data(id):
    dropbox_interface = DropboxInterface()
    product_importer = ProductImporter()
    text = dropbox_interface.get_file_contents(id)
    log.debug('-------------------- importing product data ------------------')
    product_importer.import_data(text)

@shared_task
def import_inventory_data(id):
    dropbox_interface = DropboxInterface()
    inventory_importer = InventoryImporter()
    text = dropbox_interface.get_file_contents(id)
    log.debug('-------------------- importing inventory data ----------------')
    inventory_importer.import_data(text)

@shared_task
def update_shop_inventory(company):
    log.debug(company)

    shopify_interface = ShopifyInterface()
    # update the products on shopify

    # get all the shopify products
    shopify_products = shopify_interface.get_products()
    for shop_product in shopify_products:
        log.debug(shop_product.handle)
        for shop_variant in shop_product.variants:
            log.debug(shop_variant.to_dict())
            # get the associated variant from the DB
            # local_variant = Variant.objects.get()

            # # going to need to populate the barcodes on first run.
            # # TODO: remove this once the product import
            # if shop_variant.barcode == None:
            #     # get the local_variant by sku
            #     local_variant = Variant.objects.get(sku=shop_variant.sku)
            #     # update shop_variant with the UPC of the local_products
            #     # shopify_interface()local_variant.upc
            # else:
            #     local_variant = Variant.objects.get(upc=shop_variant.barcode)



@shared_task
def get_files_to_import(account):

    dropbox_interface = DropboxInterface()
    entries = dropbox_interface.list_files(account,
                                           settings.DROPBOX_EXPORT_FOLDER)

    if entries == None:
        return False

    log.debug(entries)

    # sort by server modified time, newest first
    entries.sort(key=lambda x: x.server_modified, reverse=True)

    # TODO: Should this be factored into the importer? Should the importer
    # figure out what files it should be importing?
    # This filters the FileMetaData entries to see if they are valid import
    # files and if they are creates a list of them. An instance of
    # ImportFileMetaSet is created with the list. The instance then filters the
    # files down and returns the import set with the 
    import_files = ImportFileMetaSet([
            ImportFileMeta(e) for e in entries
            if ImportFileMeta.is_import_filemeta(e)
        ]).get_import_files()

    log.debug(import_files)

    # for each company, import the most recent product export, then import the
    # inventory file.
    for company, company_data in import_files.items():
        log.debug(company_data)
        try:
            product_id = company_data['Product'].id
            inventory_id = company_data['Inventory'].id
        except KeyError as e:
            log.debug(e)
            return False

        # call celery chain with immutable signatures so the results are
        # ignored.
        chain(
            import_product_data.si(product_id),
            import_inventory_data.si(inventory_id),
            update_shop_inventory.si(company))()


class ImportFileMeta:
    type_company_regex = r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$'
    type_company_pattern = re.compile(type_company_regex)

    def __init__(self, filemeta):
        if not self.is_import_filemeta(filemeta):
            raise Exception(
                'Invalid FileMetaData passed to ImportFileMetaconstructor')
        self.filemeta = filemeta
        self.export_type, self.company = self._get_type_company_from_filename(
            filemeta.name)

    def _get_type_company_from_filename(self, filename):
        match = self.type_company_pattern.match(filename)
        if match:
            return match.group(1,2)
        else:
            return None

    @property
    def id(self):
        return self.filemeta.id

    @classmethod
    def is_import_filemeta(cls, filemeta):
        """
        Tests a FileMetaData instance to see if it is a valid Import file.
        """
        return (cls.type_company_pattern.match(filemeta.name) and
                filemeta.path_lower.startswith(
                    settings.DROPBOX_EXPORT_FOLDER))

class ImportFileMetaSet:
    def __init__(self, import_files):
        self.files = import_files
        self.company_set = set(
            f.company for f in self.files)
        self.export_type_set = set(
            f.export_type for f in self.files)

    def get_import_files(self):
        """get the import files by company"""
        # returns True if elem has both strings present in filename
        filter_fn = lambda x: export_type == x.export_type and company == x.company

        files_by_company = dict()
        for company in self.company_set:
            files_by_company[company] = dict()
            for export_type in self.export_type_set:

                # get the first element of filtered list
                files_by_company[company][export_type] = next(
                    filter(
                        filter_fn,
                        self.files))

        return files_by_company
