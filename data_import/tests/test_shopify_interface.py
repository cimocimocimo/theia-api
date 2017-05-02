from django.test import TestCase
from django.conf import settings
import os

from ..interfaces import ShopifyInterface
import shopify, itertools

from ..models import Product, Variant, Color, Size, Company

class ShopifyInterfaceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.company = Company.objects.create(
            name='TheiaDev',
            shopify_shop_name=os.environ['DEV_SHOPIFY_SHOP_NAME'],
            shopify_api_key=['DEV_SHOPIFY_API_KEY'],
            shopify_password=['DEV_SHOPIFY_PASSWORD'])

        cls.shopify_interface = ShopifyInterface(cls.company.shop_url)

        # need to create a product
        # create Sizes 0,2,4
        sizes = [
            Size.objects.create(
                name=x)
            for x in range(0,5,2)
        ]
        # create colors red and blue with codes RED, BLU
        colors = [
            Color.objects.create(
                name=name,
                code=name[0:3].upper())
            for name in ['red', 'blue']
        ]
        cls.product = Product.objects.create(
            style_number=123456,
            season='Test 1111',
            name='Test Product',
            division='Test Division',
            description='Test description',
            archived=False,
            brand_id='123456-123',
            wholesale_usd=123,
            retail_usd=234,
            wholesale_cad=123,
            retail_cad=234,
            category='Test Category',
        )
        cls.product.colors = colors
        cls.product.sizes = sizes
        # then add variants
        cls.variants = []
        options = itertools.product(colors, sizes)
        upc_start = 620000000001
        for i, pair in enumerate(options):
            cls.variants.append(
                Variant.objects.create(
                    upc=upc_start+i,
                    product=cls.product,
                    color=pair[0],
                    size=pair[1],))

        cls.product.save()

    def test_get_products(self):
        pass
        # self.shopify_interface = ShopifyInterface()
        # products = self.shopify_interface.get_products()
        # product_count = shopify.Product.count()
        # self.assertEqual(len(products), product_count)

    def test_add_product(self):
        # Create this as a Shopify product
        # TODO: add further testing for all the other possible product attributes
        # interface = ShopifyInterface()
        # created, product = interface.add_product(self.product)
        # self.assertTrue(created)
        # self.assertTrue(shopify.Product.exists(product.id))
        pass

    def test_update_variant(self):
        pass

    @classmethod
    def tearDownClass(cls):
        # delete the test products from the store
        shopify.Product.find(title="Test Product")
        pass
