from django.conf import settings
import os, logging

log = logging.getLogger('django')

class DropboxInterface:
    import dropbox, redis

    redis_namespace = 'dropbox'
    account_key_format = '{}:{{account}}'.format(redis_namespace)
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

    def list_files(self, account, path):
        log.debug('calling list_files()')

        # TODO: Storing the cursor to only list the folder changes isn't
        # working. When I only get the changed files I don't always get the
        # Product and Inventory export files. They sometimes come together,
        # sometimes separately.
        #
        # I may need to revisit my idea of keeping a local cache of all the
        # export files on the server in a local database or redis hash. Then
        # the Product imports can check for a fresh Inventory export file once
        # they complete their import job.
        #
        # Once that is working I can revisit the idea of caching the result
        # cursor in redis to only get the changed files. till then I can't
        # use the result cursor.
        # cursor = self._get_cursor_for_account(account)
        cursor = None

        # first try continue listing the folder. If the cursor is invalid or
        # None then we get an exception and just list the full folder.
        try:
            entries, cursor = self._get_result_entries(
                self.dropbox_client.files_list_folder_continue,
                cursor=cursor)
        except Exception as e:
            log.debug(e)
            try:
                entries, cursor =  self._get_result_entries(
                    self.dropbox_client.files_list_folder,
                    path=path,
                    recursive=True)
            except Exception as e:
                log.debug(e)
                return None

        self._save_cursor_for_account(account, cursor)

        if entries == None:
            return None

        # filter out folders and deleted files.
        entries = [
            e for e in entries if
            not isinstance(e, self.dropbox.files.DeletedMetadata) and
            not isinstance(e, self.dropbox.files.FolderMetadata)]

        for e in entries:
            log.debug(type(e).__name__)

        log.debug(entries)

        return entries

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

    def _get_result_entries(self, result_cb, *args, **kwargs):
        log.debug('calling _get_result_entries()')

        entries = []
        has_more = True
        while has_more:
            log.debug(args)
            log.debug(kwargs)
            result = result_cb(*args, **kwargs)
            has_more = result.has_more
            entries.extend(result.entries)

        if len(entries) == 0:
            entries = None

        log.debug(entries)

        return entries, result.cursor

    def _get_cursor_for_account(self, account):
        # get the cursor, returns None if not present
        cursor = self.redis_client.hget(
            self._format_redis_cursor_key(account),
            account)

        # convert bytes from redis to string 
        try:
            cursor = cursor.decode('utf-8')
        except AttributeError:
            pass

        return cursor

    def _save_cursor_for_account(self, account, cursor):
        self.redis_client.hset(
            self._format_redis_cursor_key(account),
            account, cursor)

class ShopifyInterface:
    import shopify

    def __init__(self):
        "setup connection to Shopify"
        self.shopify.ShopifyResource.set_site(settings.SHOPIFY_SHOP_URL)
        self._get_products_from_shopify()

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

    def update_variant(self, variant):
        """update shopify variant from local variant"""
        pass

    def get_products(self):
        if not self.has_fetched_products:
            self._get_products_from_shopify()
        return self.products

    def _get_products_from_shopify(self):
        self.products = self._get_all_paged(self.shopify.Product.find)
        self.has_fetched_products = True

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

