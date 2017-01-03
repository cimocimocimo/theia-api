from django.test import TestCase
from django.conf import settings

from ..interfaces import DropboxInterface
from ..models import Product, Variant, ImportFileMeta, ImportFileMetaSet

class DropboxInterfaceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dropbox_interface = DropboxInterface()

        super().setUpClass()

    def test_delete_account_cursors(self):
        # create a key that should match the pattern
        self.dropbox_interface.redis_client.hset(
            self.dropbox_interface._format_redis_cursor_key('testing'),
            'testing', 'testing')

        # make sure the key was created with the correct value
        test_key_value = self.dropbox_interface.redis_client.hget(
            self.dropbox_interface._format_redis_cursor_key('testing'),
            'testing')
        self.assertEqual(test_key_value, b'testing')

        # use the interface method to reset the account cursor keys
        self.dropbox_interface.delete_account_cursors()

        # test to make sure the key was deleted
        test_key_value = self.dropbox_interface.redis_client.hget(
            self.dropbox_interface._format_redis_cursor_key('testing'),
            'testing')
        self.assertFalse(test_key_value)
