"""
Test data for this project is loaded from CSV files loaded with the importer.
"""
import os

from ..importers import ProductImporter, InventoryImporter

class LoadTestDataMixin(object):
    test_data = {
        'products': '00000000000001.SHPFY_ProductExtract_Theia.csv',
        'inventory': '00000000000001.SHPFY_InventoryExtract_Theia.csv'
    }
    test_dir = os.path.dirname(__file__)

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.product_importer = ProductImporter()
        cls.inventory_importer = InventoryImporter()

        product_data_path = '{}/{}'.format(cls.test_dir, cls.test_data['products'])
        inventory_data_path = '{}/{}'.format(cls.test_dir, cls.test_data['inventory'])
        with open(product_data_path) as f:
            cls.product_importer.import_data(f.read())

        with open(inventory_data_path) as f:
            cls.inventory_importer.import_data(f.read())

        super().setUpClass(*args, **kwargs)
