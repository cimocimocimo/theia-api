from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import re, pytz, csv

from .interfaces import DropboxInterface, RedisInterface
from .schemas import schemas

import logging

log = logging.getLogger('django')

class Color(models.Model):
    # name from Momentis database
    momentis_name = models.CharField(max_length=64)
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=8, unique=True)

    def __str__(self):
        return '{} - {}'.format(self.name, self.code)

    def correct_color_name(self, color_name):
        # make lower case
        color_name = color_name.lower()

        try:
            return ColorNameCorrection.objects.get(
                incorrect=color_name).correct
        except ColorNameCorrection.DoesNotExist:
            return color_name

    def save(self, *args, **kwargs):
        # create the corrected color name
        self.name = self.correct_color_name(self.momentis_name)
        super().save(*args, **kwargs)

# TODO: Create a fixture and import this on deploy
color_corrections = {"blk/watermelon": "black/watermelon",
                     "blush/mid": "blush/midnight",
                     "prb  - prussian blue": "prussian blue",
                     "blk/midnight": "black/midnight",
                     "blk pewter": "black pewter",
                     "blk/teal": "black/teal",
                     "blk/gold": "black/gold",
                     "champ/silver": "champagne/silver",
                     "creme": "cream",
                     "blk": 'black'}

class ColorNameCorrection(models.Model):
    incorrect = models.CharField(max_length=64, unique=True)
    correct = models.CharField(max_length=64)

class Size(models.Model):
    name = models.CharField(max_length=8)
    display_name = models.CharField(max_length=32)

    def __str__(self):
        return str(self.name)


class Product(models.Model):
    style_number = models.CharField(max_length=64, unique=True)
    season = models.CharField(max_length=128)
    name = models.CharField(max_length=256)
    department = models.CharField(max_length=64)
    division = models.CharField(max_length=64)
    available_start = models.DateField(blank=True, null=True)
    available_end = models.DateField(blank=True, null=True)
    description = models.TextField()
    archived = models.BooleanField()
    brand_id = models.CharField(max_length=64)
    wholesale_usd = models.DecimalField(max_digits=9,
                                        decimal_places=2,
                                        null=True)
    retail_usd = models.DecimalField(max_digits=9,
                                     decimal_places=2,
                                     null=True)
    wholesale_cad = models.DecimalField(max_digits=9,
                                        decimal_places=2,
                                        null=True)
    retail_cad = models.DecimalField(max_digits=9,
                                     decimal_places=2,
                                     null=True)

    # TODO: create a category hierarchy, using mptt or treebeard this could be
    # used to create the evening wear and bridal parent categories then have
    # their sub-categories.
    category = models.CharField(max_length=64)

    colors = models.ManyToManyField(Color)

    sizes = models.ManyToManyField(Size)

    def __str__(self):
        return '{} - {} - {}'.format(self.style_number, self.season, self.name)

    def in_stock(self):
        for variant in self.variant_set.all():
            if variant.inventory > 0:
                return True
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class Variant(models.Model):

    upc = models.BigIntegerField(unique=True)
    sku = models.CharField(max_length=265, unique=True)
    product = models.ForeignKey(Product, on_delete = models.CASCADE)
    color = models.ForeignKey(Color, on_delete = models.CASCADE)
    size = models.ForeignKey(Size, on_delete = models.CASCADE)

    redis = RedisInterface('variant')

    # TODO: Add a property method that gets the inventory from redis

    def generate_sku(self):
        parts = [str(self.product.style_number)]
        size = str(self.size.name)
        color = str(self.color.name)
        if size:
            parts.append(size)
        if color:
            parts.append(color)
        else:
            parts.append('none')
        return '-'.join(parts)

    def populate_sku(self):
        self.sku = self.generate_sku()
        # TODO: Remove this after we are creating the products on shopify with imported product data
        # once that happens we will be adding the upcs and skus automatically
        self.redis.client.hset(self.redis.format_key('sku_upc_map'),
                               self.sku, self.upc)

    def save(self, *args, **kwargs):
        # populate the sku
        self.populate_sku()
        super().save(*args, **kwargs)

# TODO: Use this later to create a category hierarchy.
# class Category(models.Model):
#     category

class Company(models.Model):
    name = models.CharField(unique=True, max_length=64)

class ExportType(models.Model):
    name = models.CharField(unique=True, max_length=64)

class ImportFile(models.Model):
    class Meta:
        get_latest_by = 'server_modified'

    dropbox = DropboxInterface()
    redis = RedisInterface('import_file')

    # Export Types
    PRODUCT = 'Product'
    INVENTORY = 'Inventory'

    # Import Statuses
    IMPORTED = 'IMPORTED' # Data was imported to local database/cache
    IN_PROGRESS = 'IN_PROGRESS' # In process of importing
    NOT_IMPORTED = 'NOT_IMPORTED' # Default state
    EXPIRED = 'EXPIRED' # Never imported, other, newer file of same company/type exists

    IMPORT_STATUS_CHOICES = (
        (IMPORTED, 'Imported'),
        (IN_PROGRESS, 'In Progress'),
        (NOT_IMPORTED, 'Not Imported'),
    )

    type_company_pattern = re.compile(
        r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.CSV$')
    dropbox_id = models.CharField(unique=True, max_length=64)
    path_lower = models.CharField(max_length=1024)
    filename = models.CharField(max_length=1024)
    server_modified = models.DateTimeField()
    company = models.ForeignKey(Company, on_delete = models.CASCADE)
    export_type = models.ForeignKey(ExportType, on_delete = models.CASCADE)
    import_status = models.CharField(max_length=16,
                                     choices=IMPORT_STATUS_CHOICES,
                                     default=NOT_IMPORTED)
    redis_key = models.CharField(max_length=1024, null=True)

    @classmethod
    def parse_company_export_type(cls, filename):
        """Parse the company and export_type from filename."""
        match = cls.type_company_pattern.match(filename)
        if match:
            company = match.group(2)
            export_type = match.group(1)
            return (company, export_type)
        else:
            raise ValueError(
                'Company or export type not found in filename: {}'
                .format(filename))

    def save(self, *args, **kwargs):
        # TODO: I'm not sure this is the best place to get file contents. It'll
        # work for now. But this should be moved to a class method or model
        # manager that we can call after all the import files are saved to the
        # database. The main goal is to be able to download all the import
        # files in parallel. Also be able to create or update the import files
        # in bulk to speed up the SQL queries.

        # get 12 hours ago.
        twelve_hours_ago = timezone.now() - timedelta(hours=12)

        # if server modified is within 12 hours from now
        self.server_modified = self.server_modified.replace(tzinfo=pytz.UTC)
        print('server modified: {}'.format(self.server_modified))
        print(self.filename)
        if self.server_modified > twelve_hours_ago:
            # download the file contents
            content = self._get_content_from_dropbox()
            if content:
                self._save_content_to_redis(content)

        super().save(*args, **kwargs)

    @property
    def schema(self):
        return schemas[self.export_type.name]

    # TODO: I think I could create tasks to download the file contents for both
    # files simultaneously. Use a chord to run the two download tasks then an
    # import task to import the two files sequentially.
    @property
    def content(self):
        log.debug('Getting content')
        content = self._get_content_from_redis()
        print(content)
        if content:
            return content
        else:
            return self._get_content_from_dropbox()

    @content.deleter
    def content(self):
        self.redis.client.delete(self.redis_key)

    def _get_content_from_redis(self):
        """
        Return content from redis or None
        """
        print(self.redis_key)
        # check for redis_key
        if self.redis_key:
            log.debug('getting content from redis')
            # try getting the content from redis
            content = self.redis.client.get(self.redis_key)
            print(content)
            try:
                return content.decode('utf-8')
            except Exception as e:
                log.exception(e)

        print('nothing in redis, returning none')
        return None

    def _get_content_from_dropbox(self):
        log.debug('getting content from dropbox')
        try:
            return self.dropbox.get_file_contents(self.dropbox_id)
        except Exception as e:
            log.exception(e)
            return None

    def _save_content_to_redis(self, content):
        self.redis_key = self.redis.format_key('dropbox', self.dropbox_id)
        self.redis.client.set(
            self.redis_key,
            content,
            ex=int(timedelta(hours=12).total_seconds())
        )


    def is_valid(self):
        """
        Tests a FileMetaData instance to see if it is a valid Import file.
        """
        return (self.type_company_pattern.match(self.filename) and
                self.path_lower.startswith(
                    settings.DROPBOX_EXPORT_FOLDER))

    def rows(self):
        return CSVRows(self.content, self.schema)

class CSVRows:
    """Provides an itererator interface for the ImportFile csv data"""
    def __init__(self, text, schema):
        self.text = text
        self.schema = schema
        self.columns = dict()
        self._csv_reader = self._text_to_csv(self.text)
        self._map_columns(self._csv_reader.fieldnames)

    def _map_columns(self, headers):
        # map each column's schema for each column that is in the data
        for h in headers:
            try:
                self.columns[h] = self.schema.columns[h]
            except KeyError:
                pass

    def _text_to_csv(self, text):
        lines = text.splitlines()
        # trim the trailing comma, the export files all seem to have it. By
        # removing it here we avoid creating an empty column on the right side
        # of the CSV.
        lines = [l.rstrip(',') for l in lines]
        return csv.DictReader(lines)

    def __iter__(self):
        return self

    def __next__(self):
        raw_dict = next(self._csv_reader)
        processed = dict()
        for k,v in raw_dict.items():
            try:
                processed[k] = self.columns[k].load(v)
            except IndexError:
                pass
            except ValueError as e:
                log.exception(e)
                log.warning('Row contains invalid data')
                log.warning(raw_dict)
                return None
        return processed

# redis models
class RedisModel:
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
