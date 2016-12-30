"""
The data exporter.

This takes the data in the DB and exports it to other formats and apis. It
encapsulates the logic needed to translate the local models into the formats
needed for the various destinations.
"""

from .interfaces import ShopifyInterface
from .models import Product, Variant
from .helpers import *
import re, logging

log = logging.getLogger('django')

class ExporterBase:
    pass

class ShopifyExporter(ExporterBase):
    def __init__(self):
        self.shop = ShopifyInterface()

    def zero_inventory(self):
        total = len(self.shop.products)
        for i, prod in enumerate(self.shop.products):
            print('zeroing product: {}'.format(prod.title))
            save_prod = False
            for var in prod.variants:
                if var.inventory_quantity > 0:
                    var.inventory_quantity = 0
                    save_prod = True
            if save_prod:
                prod.save()
            print('{}/{}'.format(i, total))

    def update_inventory(self):
        """Update the inventory of the products in the shop"""

        # get the products from the shop
        # loop over the shop products
        for i, shop_prod in enumerate(self.shop.products):

            # get the style number of the shop_product
            shop_style_number = get_style(shop_prod)

            if shop_style_number == None:
                log.warning('Missing style_number for product: {}'.format(shop_prod.to_dict()))
                continue

            # get the matching local product if it exists
            try:
                local_prod = Product.objects.get(style_number=shop_style_number)
            except Exception as e:
                log.warning('Missing local product for style_number: {}'
                            .format(shop_style_number))
                log.exception(e)
                continue

            # if the inventories are identical we don't need to update them
            if inventories_match(local_prod, shop_prod):
                continue

            # update the inventory in the shop with the local inventory
            local_vars = get_local_inv_dict(local_prod)
            for shop_var in shop_prod.variants:
                # make sure we have a valid UPC for the barcode
                if not is_upc_valid(shop_var.barcode):
                    log.warning(
                        'Shop variant w/ sku: {} / id: {} has invalid barcode'
                        .format(shop_var.sku, shop_var.id))
                    continue

                # update the shop_var quantity with the local quantity
                try:
                    shop_var.inventory_quantity = local_vars[shop_var.barcode]
                except Exception as e:
                    log.warning(
                        '''Shop variant w/ sku: {} / id: {}
                        is missing from local product style: {}'''
                        .format(shop_var.sku, shop_var.id,
                                local_prod.style_number))
                    log.exception(e)

            # save the product
            shop_prod.save()

            print('{}/{}'.format(i, len(self.shop.products)))


    def export(self):
        # get the products
        pass


# helpers
def get_style(prod):
    pattern = re.compile(r'^\d{6}$')
    for tag in prod.tags.split(', '):
        if pattern.match(tag) != None:
            return int(tag)
    return None

def get_local_inv_dict(local_prod):
    """Return a dict of upc: inventory items."""
    return { v.upc: v.inventory
             for v in local_prod.variant_set.all() }

def get_shop_inv_dict(shop_prod):
    """Return a dict of upc: inventory items."""
    return { v.barcode: v.inventory_quantity
             for v in shop_prod.variants
             if is_upc_valid(v.barcode) }

def inventories_match(local_prod, shop_prod):
    # their variants should match by upc.

    # create a dict of upc: quantity for each local and shop prods
    local_vars = get_local_inv_dict(local_prod)
    shop_vars = get_shop_inv_dict(shop_prod)

    # return true if the inventories for the upcs match the quantities
    return local_vars == shop_vars
