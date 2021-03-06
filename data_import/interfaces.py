from django.conf import settings
from ratelimit import rate_limited
from datetime import timedelta
import sys, os, logging

from pprint import pprint

log = logging.getLogger('django')

class DropboxInterface:
    import dropbox, redis

    redis_namespace = 'dropbox'
    # TODO: Since we are only using one account and only using a token for
    # authentication we don't need to store or even use the account variable at
    # all. We would only use accounts if people would authenticate their own
    # accounts and then used this app. We doubt that will happen. Let's remove
    # this.
    account_key_format = '{}:account:{{account}}'.format(redis_namespace)
    cursor_key_format = '{prefix}:cursor'

    def __init__(self):
        self.dropbox_client = self.dropbox.Dropbox(settings.DROPBOX_TOKEN)
        self.redis_client = self.redis.StrictRedis(host=settings.REDIS_DOMAIN,
                                                   db=settings.REDIS_DB,
                                                   port=settings.REDIS_PORT)

    @staticmethod
    def get_accounts_from_notification(data):
        return data['list_folder']['accounts']

    def upload_files(self, files, path='/'):
        for f in files:
            self.dropbox_client.files_upload(
                f.read(),
                os.path.join(path, os.path.basename(f.name)))

    def delete_file(self, path):
        self.dropbox_client.files_delete(path)

    def get_file_contents(self, id):
        filemeta, response = self.dropbox_client.files_download(id)
        return response.text

    def list_files(self, path='/', account=None):
        """Gets all files from dropbox"""

        # get cursor for account or None if account is None
        cursor = self._get_cursor_for_account(account)

        # first try continue listing the folder. If the cursor is invalid or
        # None then we get an exception and just list the full folder.
        try:
            entries, cursor = self._get_result_entries(
                cursor, path=path, recursive=True)

        except Exception as e:
            log.debug(e)
            return None

        if account and cursor:
            self._save_cursor_for_account(account, cursor)

        if entries:
            return entries
        else:
            return None

    def list_new_deleted_files(self, path='/', account=None):
        # get cursor for account or None if account is None
        cursor = self._get_cursor_for_account(account)

        # first try continue listing the folder. If the cursor is invalid or
        # None then we get an exception and just list the full folder.
        try:
            entries, cursor = self._get_result_entries(
                cursor, path=path, recursive=True)

            pprint(cursor)
            for e in entries:
                pprint(e.name)

        except Exception as e:
            log.debug(e)
            return None

        if account and cursor:
            self._save_cursor_for_account(account, cursor)

        if not entries:
            return None

        # filter out folders and deleted files.
        added_entries = [
            e for e in entries if
            not isinstance(e, self.dropbox.files.DeletedMetadata) and
            not isinstance(e, self.dropbox.files.FolderMetadata)]

        # return the deleted entries for removal
        deleted_entries = [
            e for e in entries if
            isinstance(e, self.dropbox.files.DeletedMetadata)]

        return {'added': added_entries,
                'deleted': deleted_entries}

    def has_file_ext(self, file, ext):
        return file.path_lower.endswith('.' + ext)

    def is_file_at_path(self, file, path):
        SEP = '/'
        file_path = file.path_lower.strip(SEP).split(SEP)[:-1]
        test_path = path.lower().strip(SEP).split(SEP)
        return file_path == test_path

    def _format_redis_cursor_key(self, account):
        return self.cursor_key_format.format(
            prefix=self.account_key_format.format(
                account=account))

    def delete_account_cursors(self):
        # get all the account cursor keys.
        account_keys = self.redis_client.keys(
            self.account_key_format.format(account='*'))

        # loop through and delete them.
        for k in account_keys:
            self.redis_client.delete(k)


    def _get_result_entries(self, cursor=None, *args, **kwargs):
        log.debug('calling _get_result_entries(cursor={}, args={}, kwargs={})'
                  .format(cursor, args, kwargs))

        entries = []
        has_more = True
        while has_more:

            # try the cursor continue
            if cursor is not None:
                try:
                    result = self.dropbox_client.files_list_folder_continue(cursor)
                except ApiError:
                    # invalid cursor so we set to None and get the full folder list
                    cursor = None

            if cursor is None:
                result = self.dropbox_client.files_list_folder(*args, **kwargs)

            entries.extend(result.entries)

            cursor = result.cursor
            has_more = result.has_more

        return entries, cursor

    def _get_cursor_for_account(self, account):
        if account:
            # get the cursor, returns None if not present
            cursor = self.redis_client.hget(
                self._format_redis_cursor_key(account),
                account)

            # convert bytes from redis to string 
            try:
                return cursor.decode('utf-8')
            except AttributeError as e:
                log.exception(e)

        return None

    def _save_cursor_for_account(self, account, cursor):
        key = self._format_redis_cursor_key(account)
        expire = timedelta(days=7)
        self.redis_client.hset(
            key,
            account, cursor)
        self.redis_client.expire(key, expire)

class ShopifyInterface:
    import shopify

    has_fetched_products = False
    has_fetched_variants = False

    def __init__(self, shopify_shop_url):
        "setup connection to Shopify"
        if shopify_shop_url:
            self.shopify.ShopifyResource.set_site(shopify_shop_url)
        else:
            return

        self._get_products_from_shopify()
        self.variants = list()
        for prod in self.products:
            self.variants.extend(prod.variants)

    def add_product(self, product):
        # TODO: Should some of this be in it's own class? A class that
        # encapsulates the logic that translates the csv data into our local
        # models then the local models into the Shopify store. How about an
        # exporter class? Do I even need another class that uses the importers
        # and exporters and contains the celery tasks, like a controller?
        """
        Create a new Shopify product from local Product model.

        Create a new product on Shopify with a new handle and product id and
        return a tuple with the Shopify product and Boolean for creation
        success.
        returns (Bool created, Obj product)
        """
        # TODO: this should be based off the code in product_import
        shop_product = self.shopify.Product(
            attributes={
                'title': product.name,
                'body_html': product.description,
                'vendor': product.division,
            }
        )
        # save product to get the id and the initial variant
        created = shop_product.save()
        # add options
        shop_product.options = [
            {
                'name': 'Color',
                'position': 1,
            },
            {
                'name': 'Size',
                'position': 0,
            }
        ]
        variants = product.variant_set.all()
        shop_variants = []
        for i, variant in enumerate(variants):
            shop_variant = self.shopify.Variant(
                attributes={
                    'product_id': shop_product.id,
                    'barcode': variant.upc,
                    'inventory_management': 'shopify',
                    'inventory_quantity': 0,
                    'option1': variant.color.name,
                    'option2': variant.size.name,
                }
            )
            shop_variant.save()
            shop_variants.append(shop_variant)
            log.debug(shop_variant.errors.errors)
            log.debug(shop_variant.to_dict())
            shop_product.add_variant(shop_variant)

        log.debug('saving shop_product')
        log.debug(shop_product.variants)
        shop_product.variants = shop_variants
        created = shop_product.save()
        if not created:
            log.debug(shop_product.errors.errors)

        return (created, shop_product)

    def update_shop_variant_inventory(self, shop_variant, local_variant):
        log.debug(
            'ShopifyInterface().update_shop_variant_inventory(shop_variant={})'
            .format(shop_variant))
        """update shopify variant from local variant"""
        shop_variant.inventory_quantity = local_variant.inventory
        self._update_shop_variant(shop_variant)

    @rate_limited(0.5)
    def _update_shop_variant(self, shop_variant):
        log.debug('ShopifyInterface()._update_shop_variant(shop_variant={})'
                  .format(shop_variant))
        try:
            shop_variant.save()
        except Exception as e:
            log.warning('Unable to update variant')
            log.warning(e)

    def get_products(self):
        if not self.has_fetched_products:
            self._get_products_from_shopify()
        return self.products

    def get_variants(self):
        if not self.has_fetched_variants:
            self._get_variants_from_shopify()
        return self.variants

    def _get_products_from_shopify(self):
        self.products = self._get_all_paged(self.shopify.Product.find)
        self.has_fetched_products = True

    def _get_variants_from_shopify(self):
        self.variants = self._get_all_paged(self.shopify.Variant.find)
        self.has_fetched_variants = True

    def _get_all_paged(self, page_cb, limit=250, page_numb=1):
        items = []
        has_more = True
        while has_more:
            page = page_cb(
                limit=limit,
                page=page_numb
            )
            has_more = len(page) == limit
            page_numb += 1
            items.extend(page)
        return items

class RedisInterface:
    import redis

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
        log.debug('format_key({}) returned: {}'.format(keys, key))
        return key
