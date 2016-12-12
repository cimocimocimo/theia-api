from django.test import TestCase
from django.conf import settings
import os, logging

log = logging.getLogger('django')

from ..models import Product, Variant, Color, Size

from ..importers import ProductImporter, InventoryImporter

# test_dir_path = os.path.dirname(os.path.realpath(__file__))
# product_csv_file = open(os.path.join(test_dir_path, 'products-test-data.csv'))
# inventory_csv_file = open(os.path.join(test_dir_path, 'inventory-test-data.csv'))

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
