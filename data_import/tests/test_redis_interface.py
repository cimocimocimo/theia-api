from django.test import SimpleTestCase
from django.conf import settings

from ..interfaces import RedisInterface

class RedisInterfaceTest(SimpleTestCase):
    def test_init(self):
        namespace = 'testing'
        r = RedisInterface(namespace)
        self.assertEqual(r.namespace, r.module + r.SEPARATOR + namespace)

    def test_add_namespace(self):
        namespaces = ['zero', 'one']
        r = RedisInterface(namespaces[0])
        original = r.namespace
        r.add_namespace(namespaces[1])
        self.assertEqual(r.namespace, original + r.SEPARATOR + namespaces[1])

    def test_format_key(self):
        namespace = 'testing'
        keys = ('zero', 'one', 'two')
        r = RedisInterface(namespace)
        test_key = ':'.join([r.module] + [namespace] + list(keys))
        key = r.format_key(*keys)
        self.assertEqual(key, test_key)
