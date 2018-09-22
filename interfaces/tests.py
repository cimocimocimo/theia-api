import logging, os, shopify, inspect
from django.test import TestCase
from pprint import pprint, pformat
from .shopify_interface import ShopifyInterface
from .dropbox_interface import DropboxInterface
from .redis_interface import RedisInterface

log = logging.getLogger('django')

shopify_testing_url = os.environ['SHOPIFY_TESTING_URL']

class ShopifyInterfaceTest(TestCase):
    fulfillment_service = None

    @classmethod
    def setUpClass(cls):
        log.debug('{}.setUpClass()'.format(cls.__class__.__name__))

        # pprint(inspect.getmembers(shopify.FulfillmentService, predicate=inspect.ismethod))

        # setup shopify api for access
        shopify.ShopifyResource.set_site(shopify_testing_url)
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
        pass
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

    # def test_get_level_available(self):
    #     pass
    #     shop = ShopifyInterface(shop_url=shopify_testing_url)
    #     # Get an arbitrary location to use as the import location
    #     location_id, location = next(iter(shop.locations.items()))
    #     # Get an arbitrary variant
    #     variant_id, variant = next(iter(shop.variants.items()))

    #     shop.set_level_available(location_id=location_id,
    #                              variant_id=variant_id,
    #                              available=5)

    #     available = shop.get_level_available(location_id=location_id,
    #                                          variant_id=variant_id)

    #     self.assertIsInstance(avialable, int)
    #     self.assertEqual(available, 5)

    def test_set_level_available(self):
        pass
        shop = ShopifyInterface(shop_url=shopify_testing_url)
        # Get an arbitrary variant
        vid, variant = next(iter(shop.variants.items()))

        shop.set_level_available(
            location_id=self.fulfillment_service.location_id,
            inventory_item_id=variant.inventory_item_id,
            available=5)

    @classmethod
    def tearDownClass(cls):
        log.debug('{}.tearDownClass()'.format(cls.__name__))
        # setup shopify api for access
        # shopify.ShopifyResource.set_site(shopify_testing_url)

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


