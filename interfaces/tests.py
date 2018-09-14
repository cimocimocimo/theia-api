import logging, os, shopify
from django.test import TestCase
from pprint import pprint, pformat
from .shopify_interface import ShopifyInterface
from .dropbox_interface import DropboxInterface
from .redis_interface import RedisInterface

log = logging.getLogger('django')

shopify_testing_url = os.environ['SHOPIFY_TESTING_URL']

class ShopifyInterfaceTest(TestCase):
    def setUp(self):
        log.debug('{}.setUp()'.format(self.__class__.__name__))
        # Reset the inventory and delete all inventory_levels
        
    def test_variants(self):
        # TODO: This could be refactored to test the private methods
        # _get_from_shopify() and _get_all_paged()
        shop = ShopifyInterface(shop_url=shopify_testing_url)
        # Variants should return a dict
        self.assertIsInstance(shop.variants, dict)
        # Get an arbitrary item from the dict.
        vid, variant = next(iter(shop.variants.items()))
        # Should be an instance of a variant.
        self.assertIsInstance(variant, shopify.Variant)
        # Dict key should match the variant id.
        self.assertEqual(vid, variant.id)

    def test_get_level_available(self):
        shop = ShopifyInterface(shop_url=shopify_testing_url)
        # Get an arbitrary location to use as the import location
        location_id, location = next(iter(shop.locations.items()))
        # Get an arbitrary variant
        variant_id, variant = next(iter(shop.variants.items()))

        shop.set_level_available(location_id=location_id,
                                 variant_id=variant_id,
                                 available=5)

        available = shop.get_level_available(location_id=location_id,
                                             variant_id=variant_id)

        self.assertIsInstance(avialable, int)
        self.assertEqual(available, 5)

    def test_set_level_available(self):
        shop = ShopifyInterface(shop_url=shopify_testing_url)
        # Get an arbitrary variant
        vid, variant = next(iter(shop.variants.items()))

        # self.shop.update_level(
        #     location_id=self.location.shopify_id,
        #     inventory_item_id=variant.inventory_item_id,
        #     available=new_inventory_available)

        pass
        

class DropboxInterfaceTest(TestCase):
    pass

class RedisInterfaceTest(TestCase):
    pass


