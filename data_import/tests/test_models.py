from django.test import TestCase
from django.conf import settings
from django.utils import timezone
import os, logging
from datetime import timedelta

from .mixins import LoadTestDataMixin

from ..models import Product, Variant, Color, Size, ImportFile
from ..importers import ProductImporter, InventoryImporter

log = logging.getLogger('django')

# TODO: Try using django-autofixure for running these tests
class TestProduct(LoadTestDataMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_in_stock(self):
        # variants_in_stock = Variant.objects.order_by('?').filter(inventory__gt=0)[0:10]
        # print(variants_in_stock)
        # for variant in variants_in_stock:
        #     variant.product.in_stock
        # self.assertTrue(.in_stock)
        pass

class TestVariant(TestCase):
    @classmethod
    def setUpClass(cls):
        product = Product.objects.create(
            style_number=123456,
            archived=False,
            wholesale_usd=0,
            retail_usd=0,
            retail_cad=0,
            wholesale_cad=0,
        )
        color = Color.objects.create(
            name='RED',
            code='RED',
        )
        size = Size.objects.create(
            name='X',
        )
        variant = Variant.objects.create(
            upc=12341234123412,
            product=product,
            color=color,
            size=size,
            inventory=3,
        )

        product = Product.objects.create(
            style_number=123457,
            archived=False,
            wholesale_usd=0,
            retail_usd=0,
            retail_cad=0,
            wholesale_cad=0,
        )
        color = Color.objects.create(
            name='BLK',
            code='BLK',
        )
        variant = Variant.objects.create(
            upc=12341234123413,
            product=product,
            color=color,
            size=size,
            inventory=5,
        )

        super().setUpClass()


    def test_get_by_sku(self):
        test_sku = '123456-X-red'
        variant = Variant.objects.get_by_sku(test_sku)
        self.assertEqual(variant.upc, 12341234123412)

        test_sku = '123457-X-black'
        variant = Variant.objects.get_by_sku(test_sku)
        self.assertEqual(variant.upc, 12341234123413)

class ImportFileTest(TestCase):
    def test_get_by_company_export_type(self):
        # add a few import files
        ImportFile.objects.create(
            dropbox_id='1',
            path_lower='a',
            server_modified=timezone.now(),
            company='A',
            export_type='Product',
        )
        ImportFile.objects.create(
            dropbox_id='2',
            path_lower='b',
            server_modified=timezone.now()-timedelta(1),
            company='A',
            export_type='Product',
        )
        ImportFile.objects.create(
            dropbox_id='3',
            path_lower='c',
            server_modified=timezone.now(),
            company='A',
            export_type='Inventory',
        )
        ImportFile.objects.create(
            dropbox_id='4',
            path_lower='d',
            server_modified=timezone.now()-timedelta(3),
            company='A',
            export_type='Inventory',
        )
        latest_product = ImportFile.objects.get_by_company_export_type('A', 'Product').latest()
        latest_inventory = ImportFile.objects.get_by_company_export_type('A', 'Inventory').latest()
        self.assertEqual(latest_product.dropbox_id, '1')
        self.assertEqual(latest_inventory.dropbox_id, '3')
