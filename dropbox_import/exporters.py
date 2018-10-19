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

    def __init__(self, company, fulfillment_service_id):
        self.company = company
        self.fulfillment_service_id = fulfillment_service_id
        self.inventory = Inventory(company.name)
        self.shop = ShopifyInterface(
            shop_url=company.shop_url,
            fulfillment_service_id=fulfillment_service_id)
        self._numb_products_updated = 0

    def export_data(self):

        for variant_id, variant in self.shop.variants.items():
            save_needed = False
            has_invalid_upc = False
            invalid_upcs = []

            # check for a upc
            upc = variant.barcode

            # check for valid UPC
            if not is_upc_valid(upc):
                has_invalid_upc = True
                invalid_upcs.append(upc)
                continue

            self.shop.set_level_available(variant,
                                          self.get_quantity_by_upc(upc))

        # TODO: Do I need to use this? Could I just leave the product_type
        # alone?
        # update the product collection for Theia only
        if self.company.name == 'Theia':
            # loop over the products
            for p_id, p in self.shop.products.items():
                # is the product instock?
                if self.is_product_in_stock(p) and 'Bridal' not in p.tags:
                    self.shop.update_product(p, 'product_type', 'Theia Shop')
                else:
                    # out of stock, make sure it goes in the lookbook
                    self.shop.update_product(p, 'product_type', 'Theia Collection')

        # Reset the current inventory.
        self.inventory.reset()
        
        log.info('Shopify Products Updated: {}'.format(self._numb_products_updated))

    def get_quantity_by_upc(self, upc):
        try:
            quantity = self.inventory.get_item_value(upc, 'QUANTITY')
        except Exception as e:
            log.exception(e)
            log.warning('Unable to get quantity with upc: {}'.format(upc))
        else:
            try:
                return int(quantity)
            except Exception as e:
                log.exception(e)
                log.warning(
                    'Unable to cast quantity value: {} to in for upc: {}'.format(
                        quantity, upc))
        return 0

    def is_product_in_stock(self, product):
        # get a list of variants for this product
        variant_quantities = [ self.shop.get_level_available(v)
                     for v in self.shop.variants.values()
                     if v.product_id == product.id ]
        for q in variant_quantities:
            if q > 0:
                return True
        return False


# helpers
def get_style(prod):
    pattern = re.compile(r'^\d{6}$')
    for tag in prod.tags.split(', '):
        if pattern.match(tag) != None:
            return int(tag)
    return None

