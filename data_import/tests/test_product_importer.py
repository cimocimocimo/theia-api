from django.test import TestCase
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os

from ..importers import ProductImporter, InventoryImporter
from ..models import (Size, Color, Product, Variant, ImportFile,
                      Company, ExportType)
from ..interfaces import RedisInterface
import csv

test_dir_path = os.path.dirname(os.path.realpath(__file__))

class TestProductInventoryImporters(TestCase):

    product_csv_filename = '00000000000000.SHPFY_ProductExtract_Theia.CSV'
    product_csv_path = os.path.join(test_dir_path, product_csv_filename)
    inventory_csv_filename = '00000000000000.SHPFY_InventoryExtract_Theia.CSV'
    inventory_csv_path = os.path.join(test_dir_path, inventory_csv_filename)

    @classmethod
    def setUpClass(cls):
        cls.redis = RedisInterface()

        # Mock the company and types
        company = Company.objects.create(name='Theia')
        prod_type = ExportType.objects.create(name='Product')
        inv_type = ExportType.objects.create(name='Inventory')

        # Mock the test import files
        cls.prod_import_file = ImportFile.objects.create(
            dropbox_id='1',
            path_lower=cls.product_csv_path.lower(),
            filename=cls.product_csv_filename,
            company=company, export_type=prod_type,
            server_modified=timezone.now(),
        )
        cls.inv_import_file = ImportFile.objects.create(
            dropbox_id='2',
            path_lower=cls.inventory_csv_path.lower(),
            filename=cls.inventory_csv_filename,
            company=company, export_type=inv_type,
            server_modified=timezone.now()-timedelta(1),
        )

        # open the product data csv and store the text.
        f = open(cls.product_csv_path, encoding='cp1252')
        cls.prod_import_file._save_content_to_redis(f.read())

        f = open(cls.inventory_csv_path, encoding='cp1252')
        cls.inv_import_file._save_content_to_redis(f.read())

        with open(cls.product_csv_path, encoding='cp1252') as prodcsv:
            test_reader = csv.DictReader(prodcsv)
            style_numbers = set()
            for row in test_reader:
                style_numbers.add(row['STYLE NUMBER'])
            cls.numb_prods = len(style_numbers)

        with open(cls.inventory_csv_path, encoding='cp1252') as invcsv:
            test_reader = csv.DictReader(invcsv)
            cls.test_inv_item = next(test_reader)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_import_data(self):
        importer = ProductImporter()
        importer.import_data(self.prod_import_file)

        prod = Product.objects.all().first()
        self.assertIsInstance(prod, Product)
        self.assertEqual(self.numb_prods, Product.objects.count())

        inv_importer = InventoryImporter()
        inv_importer.import_data(self.inv_import_file)

        # check for the sku_upc_map
        self.assertTrue(self.redis.client.exists('variant:sku_upc_map'))

        # ensure sku_upc_map has a ttl set
        self.assertGreater(self.redis.client.ttl('variant:sku_upc_map'), 0)
