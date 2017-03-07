import os

from django.test import TestCase, SimpleTestCase, TransactionTestCase
from django.conf import settings

import shopify
from ..models import Product, Variant, Color, Size
from ..exporters import *
from ..importers import ProductImporter, InventoryImporter

shopify.ShopifyResource.set_site(settings.SHOPIFY_SHOP_URL)

class MockShopProduct:
    def __init__(self, *args, **kwargs):
        self.tags = kwargs.get('tags')

class TestShopifyExporter(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        cls.mock_shop_prod = MockShopProduct(
            tags='Season 2015, 123456, Season, 2015')

        cls.bridal_prod = MockShopProduct(
            tags='Bridal, Bridal Fall, Bridal Fall 2017, 223355')

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

    def test_is_product_for_sale(self):
        exporter = InventoryExporter()
        self.assertFalse(exporter.is_product_for_sale(self.bridal_prod))
        pass
