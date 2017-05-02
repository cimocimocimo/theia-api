from django.test import SimpleTestCase
from django.conf import settings
import logging

from ..interfaces import RedisInterface
from ..models import Inventory

log = logging.getLogger('django')

class IventoryTest(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        cls.inventory = Inventory('Company')
        super().setUpClass()

    def test_init(self):
        self.assertEqual(self.inventory.redis.namespace, 'Company:inventory')
        self.assertEqual(self.inventory.item_set_key_name, 'Company:inventory:upcs')
        self.assertEqual(self.inventory.item_key_prefix, 'upc')

    def test_add_get_item(self):
        key = '012345678912'
        item = {
            'upc': '112345678912',
            'quantity': '6',
            'date': 'IMMEDIATE',
        }
        self.inventory.add_item(key, item)
        gotten_item = self.inventory.get_item(key)
        self.assertEqual(item, gotten_item)
