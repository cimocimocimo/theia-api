from django.test import SimpleTestCase, override_settings
from django.conf import settings
from time import sleep
import os

from ..models import Product, Variant, Color, Size
from ..importers import ProductImporter, InventoryImporter
from ..interfaces import ShopifyInterface, DropboxInterface

os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8000'

test_dir_path = os.path.dirname(os.path.realpath(__file__))
product_csv_file = open(os.path.join(test_dir_path,
                                     '20161211190028.SHPFY_ProductExtract_Theia.CSV'
                                     # '00000000000000.SHPFY_ProductExtract_Theia.CSV'
), 'rb')
inventory_csv_file = open(os.path.join(test_dir_path,
                                       '20161211190032.SHPFY_InventoryExtract_Theia.CSV'
                                       # '00000000000000.SHPFY_InventoryExtract_Theia.CSV'

), 'rb')

"""
This requires the development server to be running, not the Live Test Server.
this is so that the Celery worker task can access the same DB as the rest of
the code.

This test code is only meant to trigger the webhook to kick off the import process.

This tests how all the parts work together. It simulates what happens when a
new export file is produced and the import process is kicked off. It will add
files to the dropbox to trigger the webhook.
then the celery tasks are run to import into the database
then the celery tasks to update the inventory in Shopify are created
Once complete, the import files are deleted from dropbox, the imported products
in shopify are deleted, the redis database is cleared

Things to test:
- initial import of most recent data
  - gets all the most recent data from the dropbox and imports it
  - imports all the current products from Shopify
  - scans shopify product variants by sku
  - 
"""
test_folder = '/test'
@override_settings(DROPBOX_EXPORT_FOLDER=test_folder)
class TestImportProcess(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        # cls.shopify_interface = ShopifyInterface()
        cls.dropbox_interface = DropboxInterface()
        # delete test files before test run
        try:
            cls.dropbox_interface.delete_file(test_folder)
        except:
            pass
        super().setUpClass()

    def test_import(self):
        # upload test data to dropbox
        self.dropbox_interface.upload_files(
            [product_csv_file, inventory_csv_file],
            settings.DROPBOX_EXPORT_FOLDER)

    @classmethod
    def tearDownClass(cls):
        pass
