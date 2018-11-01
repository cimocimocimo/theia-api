import logging, redis
from django.conf import settings
from pprint import pprint, pformat

log = logging.getLogger('django')

class RedisInterface:
    client = redis.StrictRedis(host=settings.REDIS_DOMAIN,
                               db=settings.REDIS_DB,
                               port=settings.REDIS_PORT)

    SEPARATOR = ':'

    def __init__(self, namespace=None):
        self.namespace = ''
        if namespace:
            self.add_namespace(namespace)

    def add_namespace(self, namespace):
        if self.namespace:
            self.namespace += self.SEPARATOR + namespace
        else:
            self.namespace = namespace

    def format_key(self, *keys):
        key = self.SEPARATOR.join(
            [self.namespace] + [str(k) for k in keys])
        return key

