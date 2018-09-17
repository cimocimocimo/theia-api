"""
The data exporter.

This takes the data in the DB and exports it to other formats and apis. It
encapsulates the logic needed to translate the local models into the formats
needed for the various destinations.
"""

import re, logging
from interfaces import ShopifyInterface, RedisInterface
from core.models import Inventory
from csv_parser.helpers import is_upc_valid

log = logging.getLogger('django')

class InventoryExporter():
    """
    Export the latest inventory data to the shops for each company.
    """

    def __init__(self, company, location_id):
        self.company = company
        self.location_id = location_id
        self.inventory = Inventory(company.name)
        self.shop = ShopifyInterface(shop_url=company.shop_url)
        self._numb_products_updated = 0

    def export_data(self):

        # get the products from shopify
        self._products = self.shopify.get_products()

        # loop over the products
        for p in self._products:
            # flag for saving
            save_needed = False
            has_invalid_upc = False
            invalid_upcs = []

            # loop over the variants
            for v in p.variants:

                # check for a upc
                upc = v.barcode

                # check for valid UPC
                if not is_upc_valid(upc):
                    has_invalid_upc = True
                    invalid_upcs.append(upc)
                    continue

                # update the variant quantity by upc
                original_quantity = v.inventory_quantity
                v.inventory_quantity = self.get_quantity_by_upc(upc)
                if original_quantity != v.inventory_quantity:
                    save_needed = True

            # TODO: Do I need to use this? Could I just leave the product_type
            # alone?
            # update the product collection for Theia only
            if self.company.name == 'Theia':
                # is the product instock?
                if self.is_product_in_stock(p) and 'Bridal' not in p.tags:
                    # ensure the product type is correct
                    if p.product_type != 'Theia Shop':
                        p.product_type = 'Theia Shop'
                        save_needed = True

                else:
                    # out of stock, make sure it goes in the lookbook
                    if p.product_type != 'Theia Collection':
                        p.product_type = 'Theia Collection'
                        save_needed = True

            if has_invalid_upc:
                log.warning(
                    'Product handle {} has invalid UPCs: {}'
                    .format(p.handle, invalid_upcs))

            if save_needed:
                self._numb_products_updated += 1
                p.save()

        # Reset the current inventory.
        self.inventory.reset()
        
        log.info('Shopify Products Updated: {}'.format(self._numb_products_updated))

    def get_quantity_by_upc(self, upc):
        try:
            quantity = self.inventory.get_item_value(upc, 'QUANTITY')
        except Exception as e:
            log.exception(e)
            log.warning('Unable to get quantity with upc: {}'.format(upc))
            return 0
        else:
            try:
                return int(quantity)
            except Exception as e:
                log.exception(e)
                log.warning(
                    'Unable to cast quantity value: {} to in for upc: {}'.format(
                        quantity, upc))

    def is_product_in_stock(self, product):
        for v in product.variants:
            if v.inventory_quantity and v.inventory_quantity > 0:
                return True
        return False


# helpers
def get_style(prod):
    pattern = re.compile(r'^\d{6}$')
    for tag in prod.tags.split(', '):
        if pattern.match(tag) != None:
            return int(tag)
    return None

