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
import os

log = logging.getLogger('django')
dbx = dropbox.Dropbox(settings.DROPBOX_TOKEN)
redis_client = redis.StrictRedis(host=settings.REDIS_DOMAIN,
                                 db=settings.REDIS_DB,
                                 port=settings.REDIS_PORT)
export_folder = settings.DROPBOX_EXPORT_FOLDER
redis_namespace = 'dropbox'
type_company_pattern = re.compile(r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$')

def start_dropbox_notification_tasks(data):
    log.debug(data)
    # Process request in worker task
    # TODO: this should be factored in to the DropboxInterface
    for account in data['list_folder']['accounts']:
        handle_webhook.delay(account)

# TODO: fix the redis caching, it's currently pulling the entire file list from
# dropbox.
# TODO: factor the dropbox specific stuff into the DropboxInterface. 
@shared_task
def handle_webhook(account):
    log.debug('calling handle_webhook()')

    # For data associated with this dropbox account
    account_key = '{}:{}'.format(redis_namespace, account)

    # cursor for the user (None the first time)
    cursor_key = '{}:cursors'.format(account_key)
    # DEBUG cursor = redis_client.hget(cursor_key, account)
    cursor = None
    # convert bytes from redis to string 
    try:
        cursor = cursor.decode('utf-8')
    except AttributeError:
        pass

    # fetch the results
    # TODO: factor this into a single classmethod in DropboxInterface. This
    # should be a self contained method for getting a list of all files or just
    # the ones that have changed if we have an existing cursor.
    files = list()
    has_more = True
    while has_more:
        if cursor is None:
            result = dbx.files_list_folder(path='', recursive=True)
        else:
            result = dbx.files_list_folder_continue(cursor)

        for entry in result.entries:
            # log.debug(entry)
            # toss entries not in the export folder and non-csv files
            # TODO: this contains some logic specific to the import process and
            # some specific to dropbox. Should be split into the appropriate
            # files. IE the instance checking should be dropbox and the
            # export_folder and file extention check should be moved to the
            # importer.
            # TODO: add the filename filtering using the type_company_pattern regex.
            if (not entry.path_lower.startswith(export_folder) or
                not entry.path_lower.endswith('.csv') or
                isinstance(entry, dropbox.files.DeletedMetadata) or
                isinstance(entry, dropbox.files.FolderMetadata)):
                continue

            # save the metadata
            files.append(entry)

        # Update cursor
        cursor = result.cursor
        redis_client.hset(cursor_key, account, cursor)

        # Repeat only if there's more to do
        has_more = result.has_more

    log.debug(files)

    # TODO: factor this into the importer or the DropboxInterface
    # get the latest product and inventory file by company
    # the product import needs to be run before the inventory import

    # sort by server modified time
    files.sort(key=lambda x: x.server_modified, reverse=True)

    # get set of company names and export types
    export_company_set = set([_get_type_company_from_filename(f.name) for f in files])
    log.debug('export_company_set')
    log.debug(export_company_set)

    # get sets of company and export type names
    export_set = set( pair[0] for pair in export_company_set )
    company_set = set( pair[1] for pair in export_company_set )

    # split files by company name
    files_by_company = dict()
    for company in company_set:
        files_by_company[company] = dict()
        for export_type in export_set:
            # returns True if elem has both strings present in filename
            filter_fn = lambda x: export_type in x.name and company in x.name

            # get the first element of filtered list
            files_by_company[company][export_type] = next(filter(filter_fn, files))

    log.debug('company_set')
    log.debug(company_set)
    log.debug(files_by_company)

    # for each company, import the most recent product export, then import the
    # inventory file.
    for company, company_data in files_by_company.items():
        log.debug(company_data)
        product_id = company_data['Product'].id
        inventory_id = company_data['Inventory'].id
        # call celery chain with immutable signatures so the results are ignored.
        chain(
            import_product_data.si(product_id),
            import_inventory_data.si(inventory_id),
            update_shop_inventory.si(company),
        )()

@shared_task
def import_product_data(id):
    dropbox_interface = DropboxInterface()
    product_importer = ProductImporter()
    text = dropbox_interface.get_file_contents(id)
    log.debug('-------------------- importing product data --------------------')
    product_importer.import_data(text)

@shared_task
def import_inventory_data(id):
    dropbox_interface = DropboxInterface()
    inventory_importer = InventoryImporter()
    text = dropbox_interface.get_file_contents(id)
    log.debug('-------------------- importing inventory data --------------------')
    inventory_importer.import_data(text)

@shared_task
def update_shop_inventory(company):
    log.debug(company)

    shopify_interface = ShopifyInterface()
    # update the products on shopify

    # get all the shopify products
    shopify_products = shopify_interface.get_products()
    for shop_product in shopify_products:
        log.debug(product.handle)
        for shop_variant in shop_product.variants:
            log.debug(shop_variant.to_dict())
            # get the associated variant from the DB
            local_variant = Variant.objects.get()

            # going to need to populate the barcodes on first run.
            # TODO: remove this once the product import
            if shop_variant.barcode == None:
                # get the local_variant by sku
                local_variant = Variant.objects.get(sku=shop_variant.sku)
                # update shop_variant with the UPC of the local_products
                shopify_interface()local_variant.upc
            else:
                local_variant = Variant.objects.get(upc=shop_variant.barcode)


def _get_type_company_from_filename(filename):
    match = type_company_pattern.match(filename)
    if match:
        return match.group(1,2)
    else:
        return None
