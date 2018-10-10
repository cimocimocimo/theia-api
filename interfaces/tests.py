import logging, os, inspect
from pprint import pprint, pformat

import shopify
from django.test import TestCase

from .shopify_interface import ShopifyInterface
from .dropbox_interface import DropboxInterface
from .redis_interface import RedisInterface


log = logging.getLogger('development')
shopify_testing_url = os.environ['SHOPIFY_TESTING_URL']
# setup shopify api for access
shopify.ShopifyResource.set_site(shopify_testing_url)


class ShopifyInterfaceTest(TestCase):

    fulfillment_service = None

    @classmethod
    def setUpClass(cls):
        log.debug('{}.setUpClass()'.format(cls.__name__))

        super().setUpClass()
        
        # DEBUG: Used for inspecting the poorly documented pyactiveresources
        # from returned by the Shopify API.
        # pprint(inspect.getmembers(shopify.FulfillmentService, predicate=inspect.ismethod))

    @classmethod
    def setUpTestData(cls):
        log.debug('{}.setUpTestData()'.format(cls.__name__))

        # get the testing fulfillment service
        try:
            cls.fulfillment_service = shopify.FulfillmentService.find_first(
                handle='testing-fulfillment-service',
                scope='all')
        except Exception as e:
            log.debug(pformat(e))
            log.debug('Missing "testing-fulfillment-service", please create')

    def setUp(self):
        log.debug('{}.setUp()'.format(self.__class__.__name__))
        
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

    def test_get_set_level_available(self):

        # get the testing fulfillment service, normally we would get this value
        # from the local database.
        service = shopify.FulfillmentService.find(
            scope='all',
            name='Testing Fulfillment Service')[0]
        
        shop = ShopifyInterface(
            shop_url=shopify_testing_url,
            default_location_id=service.location_id)

        # Get an arbitrary variant
        variant_id, variant = next(iter(shop.variants.items()))

        # set the inventory level manually
        shopify.InventoryLevel.set(
            inventory_item_id=variant.inventory_item_id,
            location_id=service.location_id,
            available=0)

        # set it's inventory level
        shop.set_level_available(variant, 99)
        # get it back
        available = shopify.InventoryLevel.find(
            inventory_item_ids=variant.inventory_item_id,
            location_ids=service.location_id)[0].available
        self.assertEqual(99, available)

        # set the inventory level manually
        shopify.InventoryLevel.set(
            inventory_item_id=variant.inventory_item_id,
            location_id=service.location_id,
            available=44)
        # reset inventory levels manually
        shop.inventory_levels = None
        # test get method
        available = shop.get_level_available(variant)
        self.assertEqual(44, available)

        shop.set_level_available(variant, 0)

    def test_reset_inventory(self):
        # get the testing fulfillment service, normally we would get this value
        # from the local database.
        service = shopify.FulfillmentService.find(
            scope='all',
            name='Testing Fulfillment Service')[0]
        
        shop = ShopifyInterface(
            shop_url=shopify_testing_url,
            default_location_id=service.location_id)

        # Get an arbitrary variant
        variant_id, variant = next(iter(shop.variants.items()))

        # set the inventory level manually
        level = shopify.InventoryLevel.set(
            inventory_item_id=variant.inventory_item_id,
            location_id=service.location_id,
            available=99)

        self.assertEqual(99, level.available)

        # reset the inventory to 0
        shop.reset_inventory()

        # get the inventory level back from shopify
        level = shopify.InventoryLevel.find(
            inventory_item_ids=variant.inventory_item_id,
            location_ids=service.location_id,)[0]

        self.assertEqual(0, level.available)


    def tearDown(self):
        log.debug('{}.tearDown()'.format(self.__class__.__name__))

    @classmethod
    def tearDownClass(cls):
        log.debug('{}.tearDownClass()'.format(cls.__name__))

        return

        # Reset the inventory and delete all inventory_levels
        levels = shopify.InventoryLevel.find(
            location_ids=str(cls.fulfillment_service.location_id))
        log.debug(pformat(levels))
        for l in levels:
            log.debug(pformat(l.to_dict()))
            log.debug(pformat(inspect.getmembers(l, predicate=inspect.ismethod)))
            # l.delete()

        # Delete the fulfillment service


class DropboxInterfaceTest(TestCase):
    pass

class RedisInterfaceTest(TestCase):
    pass


