from django.test import TestCase
from django.conf import settings
import os

from ..importers import ProductImporter, InventoryImporter
from ..models import Size, Color, Product, Variant
import csv

test_dir_path = os.path.dirname(os.path.realpath(__file__))

class TestProductInventoryImporters(TestCase):

    product_csv_file_path = os.path.join(test_dir_path,
                                         '00000000000000.SHPFY_ProductExtract_Theia.CSV')
    inventory_csv_file_path = os.path.join(test_dir_path,
                                           '00000000000000.SHPFY_InventoryExtract_Theia.CSV')

    @classmethod
    def setUpClass(cls):
        # open the product data csv and store the text.
        f = open(cls.product_csv_file_path, encoding='cp1252')
        cls.product_csv_text = f.read()

        f = open(cls.inventory_csv_file_path, encoding='cp1252')
        cls.inventory_csv_text = f.read()

        with open(cls.product_csv_file_path, encoding='cp1252') as prodcsv:
            test_reader = csv.DictReader(prodcsv)
            style_numbers = set()
            for row in test_reader:
                style_numbers.add(row['STYLE NUMBER'])
            cls.numb_prods = len(style_numbers)

        with open(cls.inventory_csv_file_path, encoding='cp1252') as invcsv:
            test_reader = csv.DictReader(invcsv)
            cls.test_inv_item = next(test_reader)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_import_data(self):
        importer = ProductImporter()
        importer.import_data(self.product_csv_text)
        # should create a DictReader and the first column name should be
        # "SEASON".
        self.assertIsInstance(importer.csv, csv.DictReader)
        self.assertEqual('SEASON', importer.csv.fieldnames[0])
        prod = Product.objects.all().first()
        self.assertIsInstance(prod, Product)
        self.assertEqual(self.numb_prods, Product.objects.count())

        inv_importer = InventoryImporter()
        inv_importer.import_data(self.inventory_csv_text)

        self.assertIsInstance(inv_importer.csv, csv.DictReader)
        self.assertEqual('UPC', inv_importer.csv.fieldnames[0])
        variant = Variant.objects.get(upc=self.test_inv_item['UPC'])
        # check to make sure the inventory matches
        self.assertEqual(variant.inventory, int(self.test_inv_item['QUANTITY']))
