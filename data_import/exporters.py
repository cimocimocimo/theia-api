"""
The data exporter.

This takes the data in the DB and exports it to other formats and apis. It
encapsulates the logic needed to translate the local models into the formats
needed for the various destinations.
"""

from .interfaces import ShopifyInterface, RedisInterface
from .models import Product, Variant, Inventory
from .helpers import *
import re, logging

log = logging.getLogger(__name__).getChild('export')

class ExporterBase:
    def __init__(self):
        pass

    def export_data(self):
        pass

class InventoryExporter(ExporterBase):
    """
    Export the latest inventory data to the shops for each company.

    TODO: Get companies from the database - just Theia for now
    """
    def __init__(self):
        # TODO: Get the company name by looping over the companies
        # TODO: Associate the Shopify login info with the company somehow. (use a dict in settings?)
        self.redis = RedisInterface('') # TODO: remove this when not needed.
        self.shopify = ShopifyInterface()
        self.inventory = Inventory('Theia')
        super().__init__()

    # TODO: remove this once we are adding products to shopify automatically.
    def get_upc_by_sku(self, sku):
        try:
            raw_upc = self.redis.client.hget('variant:sku_upc_map', sku)
            return raw_upc.decode('utf-8')
        except:
            log.warning('Shopify product with sku: {} missing UPC'.format(sku))
            pass

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

    def export_data(self):
        # get all the shopify products
        # TODO: Create a Model for shopify objects. provide interface to
        # Shopify to get the objects and cache them in redis
        products = self.shopify.get_products()

        # loop over the products
        for p in products:
            save_needed = False

            # loop over the variants
            for v in p.variants:

                # check for a upc
                upc = v.barcode

                # TODO: remove this once we are adding products to shopify automatically.
                if not is_upc_valid(upc):

                    # get upc from sku-upc mapping
                    upc = self.get_upc_by_sku(v.sku)

                    if upc:
                        print('got upc: {} with sku: {}'.format(upc, v.sku))
                        v.barcode = upc
                        print('barcode: {}'.format(v.barcode))
                        save_needed = True
                    else:
                        # no upc so we can't find the quantity by upc..
                        continue

                if is_upc_valid(upc):
                    # update the variant quantity by upc
                    original_quantity = v.inventory_quantity
                    v.inventory_quantity = self.get_quantity_by_upc(upc)
                    if original_quantity != v.inventory_quantity:
                        save_needed = True
                else:
                    # we don't have a valid upc, raise an exception
                    raise Exception(
                        'Got invalid upc from redis: {}'.format(upc))

            # is the product instock?
            if self.is_product_in_stock(p) and self.is_product_available(p):
                # ensure the product type is correct
                if p.product_type != 'Theia Shop':
                    p.product_type = 'Theia Shop'
                    save_needed = True

            else:
                # out of stock, make sure it goes in the lookbook
                if p.product_type != 'Theia Collection':
                    p.product_type = 'Theia Collection'
                    save_needed = True

            if save_needed:
                print('saving product: {}'.format(p.title))
                p.save()
            else:
                print('skipping')

    def is_product_in_stock(self, p):
        for v in p.variants:
            if v.inventory_quantity and v.inventory_quantity > 0:
                return True
        return False

    def is_product_available(self, p):
        return True

        # get the style number from the tags
        # tags is returned as a single string. Tags are separated by ', '
        style_number_pattern = re.compile(r'\d{6}')
        match = style_number_pattern.search(p.tags)
        if match:
            style_number = match.group()
        else:
            # product has no style number so we shouldn't update the
            # inventory
            return false

        # get the local product object
        local_prod = Product.objects.get(style_number=style_number)
        return local_prod.available
        

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
