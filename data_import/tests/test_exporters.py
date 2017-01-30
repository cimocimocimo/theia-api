import os

from django.test import TestCase, SimpleTestCase, TransactionTestCase
from django.conf import settings

# load in test data setup methods
from .mixins import *

import shopify
from ..models import Product, Variant, Color, Size
from ..exporters import *
from ..importers import ProductImporter, InventoryImporter

shopify.ShopifyResource.set_site(settings.SHOPIFY_SITE_URL)

class MockShopProduct:
    tags = 'Season 2015, 123456, Season, 2015'

class TestShopifyExporter(LoadTestDataMixin, TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_shop_prod = MockShopProduct()

        super().setUpClass()
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_update_inventory(self):
        pass
        # self.exporter.update_inventory()

    def test_get_style(self):
        style = get_style(self.mock_shop_prod)
        self.assertEqual(style, 123456)

    def test_get_local_inv_dict(self):
        test_inv = {638700000176: 7,
                    638700000177: 2,
                    638700000178: 9,
                    638700000179: 4,
                    638700000180: 9,
                    638700000171: 0,
                    638700000172: 3,
                    638700000173: 3,
                    638700000174: 6,
                    638700000175: 3}
        local_prod = Product.objects.get(style_number=882327)
        local_inventory = get_local_inv_dict(local_prod)
        self.assertEqual(test_inv, local_inventory)


    def test_get_shop_inv_dict(self):
        local_prod = Product.objects.get(style_number=882327)
        shop_prod = shopify.Product(attributes={
            'title': 'Test Product',
        })
        variants = [
            
        ]
        shop_prod.add
        test_inv = {638700000176: 7,
                    638700000177: 2,
                    638700000178: 9,
                    638700000179: 4,
                    638700000180: 9,
                    638700000171: 0,
                    638700000172: 3,
                    638700000173: 3,
                    638700000174: 6,
                    638700000175: 3}
