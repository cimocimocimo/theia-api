import logging
from django.db import models
from datetime import timedelta
from pprint import pprint, pformat

log = logging.getLogger('django')

from interfaces import RedisInterface, ShopifyInterface

class Company(models.Model):
    name = models.CharField(unique=True, max_length=64)
    should_import = models.BooleanField(default=False)
    # Shopify
    shopify_shop_name = models.CharField(unique=True, max_length=256, blank=True, null=True)
    shopify_api_key = models.CharField(max_length=256, blank=True, null=True)
    shopify_password = models.CharField(max_length=256, blank=True, null=True)
    # flag for checking we can connect to Shopify with these values.
    shopify_url_is_valid = models.BooleanField(default=False)
    # used for checking if the values changed on save
    __shopify_shop_name = None
    __shopify_api_key = None
    __shopify_password = None

    @property
    def has_shop_url(self):
        if (self.shopify_shop_name
            and self.shopify_api_key
            and self.shopify_password):
            return True
        return False

    @property
    def shop_url(self):
        if (self.has_shop_url):
            return 'https://{}:{}@{}.myshopify.com/admin'.format(
                self.shopify_api_key,
                self.shopify_password,
                self.shopify_shop_name)
        return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # store the original values to compare with on save
        self.__shopify_shop_name = self.shopify_shop_name
        self.__shopify_api_key = self.shopify_api_key
        self.__shopify_password = self.shopify_password

    def save(self, *args, **kwargs):
        # check to see if the Shopify values have been changed
        if (self.has_shop_url and (
                self.__shopify_shop_name != self.shopify_shop_name
                or self.__shopify_api_key != self.shopify_api_key
                or self.__shopify_password != self.shopify_password)):
            # something's changed, make sure the shop_url is valid.
            try:
                shop = ShopifyInterface(shop_url=self.shop_url)
            except:
                self.shopify_url_is_valid = False
            else:
                self.shopify_url_is_valid = True

        super().save(*args, **kwargs)
        # populate the fulfillment services for this company, called after the
        # main save action

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)

    def __str__(self):
        return '{}'.format(self.name)


class FulfillmentService(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    location_id = models.BigIntegerField()
    handle = models.CharField(max_length=256, blank=True, null=True)
    name = models.CharField(max_length=256, blank=True, null=True)
    is_import_destination = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure we only have one import destination per company
        if self.is_import_destination:
            # Change other instances of this company fulfillment service that
            # are True to False.
            self.__class__.objects.filter(
                is_import_destination=True,
                company=self.company,
            ).update(
                is_import_destination=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return '{}'.format(self.name)


# redis models
class RedisModel:
    """
    Model for storing sets of objects in Redis

    python redis methods to use
    .hget(name, key) - returns value for hash key
    .hgetall(name) - returns dict
    .hset(name, key, value) - individually set keys/values for hash
    .hmset(name, mapping [dict]) - sets multiple values for hash with name
    .expire(name, seconds) - seconds can be an integer or timedelta obj.
    .sadd(name, value) - add value to set
    """
    def __init__(self):
        self.redis = RedisInterface()
        self.items = dict()
        self.item_key_set = set()

    def add_item(self, key, item):
        self.items[key] = item
        self.item_key_set.add(key)

        # add key to redis set
        self.redis.client.sadd(self.item_set_key_name, key)

        # add item hash to redis
        key = self._format_item_key(key)
        self.redis.client.hmset(key, item)
        self.redis.client.expire(key, timedelta(hours=12))

    def get_item(self, key):
        key = self._format_item_key(key)
        item = self.redis.client.hgetall(key)
        return {
            k.decode('utf-8'): v.decode('utf-8')
            for k,v in item.items()
        }

    def get_item_value(self, key, prop):
        key = self._format_item_key(key)
        value = self.redis.client.hget(key, prop)
        try:
            return value.decode('utf-8')
        except Exception as e:
            log.exception(e)
            log.warning('Unable to decode value: {} for prop: {}, key: {}'.format(value, prop, key))

    def _format_item_key(self, key):
        return self.redis.format_key(self.item_key_prefix, key)

    def _save_item_set_key(self, key):
        self.item_set_key_name = self.redis.format_key(key)

    def reset(self):
        # delete the key set
        self.redis.client.delete(self.item_set_key_name)

        # delete all the item hashes
        m = self._format_item_key('*')
        for k in self.redis.client.scan_iter(match=m):
            self.redis.client.delete(k)

class Inventory(RedisModel):
    def __init__(self, company_name):
        super().__init__()
        # set key prefix to 'CompanyName:inventory'
        self.redis.add_namespace(company_name)
        self.redis.add_namespace('inventory')

        # set the item_set_key
        self._save_item_set_key('upcs')

        # name the item key prefix
        self.item_key_prefix = 'upc'
