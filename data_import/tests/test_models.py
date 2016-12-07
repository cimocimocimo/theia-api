from django.test import TestCase
from django.conf import settings
import os

from ..models import Product, Variant, Color, Size

from ..importers import ProductImporter, InventoryImporter

test_dir_path = os.path.dirname(os.path.realpath(__file__))
product_csv_file = open(os.path.join(test_dir_path, 'products-test-data.csv'))
inventory_csv_file = open(os.path.join(test_dir_path, 'inventory-test-data.csv'))

# TODO: Try using django-autofixure for running these tests
class TestProduct(TestCase):

    # @classmethod
    # def setUpClass(cls):
    #     cls.product_importer = ProductImporter()
    #     cls.inventory_importer = InventoryImporter()
    #     cls.product_importer.import_data(product_csv_file.read())
    #     cls.inventory_importer.import_data(inventory_csv_file.read())

    #     super().setUpClass()

    def test_in_stock(self):
        # variants_in_stock = Variant.objects.order_by('?').filter(inventory__gt=0)[0:10]
        # print(variants_in_stock)
        # for variant in variants_in_stock:
        #     variant.product.in_stock
        # self.assertTrue(.in_stock)
        pass
