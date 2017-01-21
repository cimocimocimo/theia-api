from django.test import TestCase
from django.conf import settings

from ..interfaces import DropboxInterface

class DropboxInterfaceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dropbox = DropboxInterface()

        super().setUpClass()

    def test_delete_account_cursors(self):
        # create a key that should match the pattern
        self.dropbox.redis_client.hset(
            self.dropbox._format_redis_cursor_key('testing'),
            'testing', 'testing')

        # make sure the key was created with the correct value
        test_key_value = self.dropbox.redis_client.hget(
            self.dropbox._format_redis_cursor_key('testing'),
            'testing')
        self.assertEqual(test_key_value, b'testing')

        # use the interface method to reset the account cursor keys
        self.dropbox.delete_account_cursors()

        # test to make sure the key was deleted
        test_key_value = self.dropbox.redis_client.hget(
            self.dropbox._format_redis_cursor_key('testing'),
            'testing')
        self.assertFalse(test_key_value)

    def test_save_cursor_for_account(self):
        # save a mock cursor
        self.dropbox._save_cursor_for_account('testaccount', 'testcursor')

        # get the cursor key
        key = self.dropbox._format_redis_cursor_key('testaccount')

        # check for a ttl on the key
        ttl = self.dropbox.redis_client.ttl(key)

        # assert the ttl is greater than 0
        self.assertGreater(ttl, 0)
