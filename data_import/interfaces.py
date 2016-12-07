from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.conf import settings
from hashlib import sha256
import json, hmac, os, logging

from pprint import pprint

log = logging.getLogger('django')

class DropboxInterface:
    import dropbox

    def __init__(self):
        self.dropbox_client = self.dropbox.Dropbox(settings.DROPBOX_TOKEN)

    @classmethod
    def verify_webhook(cls, request):
        challenge = request.GET.get('challenge')
        if challenge is not None:
            return HttpResponse(challenge)
        else:
            return HttpResponseBadRequest('Missing "challenge" parameter.')

    @classmethod
    def process_notification(cls, request):
        # Make sure this is a valid request from Dropbox
        if not settings.DEBUG and not cls.is_request_valid(request):
            return HttpResponseForbidden()

        try:
            raw_body = request.body.decode('utf-8')
        except UnicodeError:
            return HttpResponseBadRequest()

        try:
            data = json.loads(raw_body)
        except ValueError:
            return HttpResponseBadRequest()

        # importing here prevents import errors. not sure why. - AC
        from .tasks import start_dropbox_notification_tasks
        start_dropbox_notification_tasks(data)

        return HttpResponse('OK')

    @classmethod
    def is_request_valid(cls, request):
        # HMAC verification
        return hmac.compare_digest(
            request.META['HTTP_X_DROPBOX_SIGNATURE'],
            cls.generate_signature(request)
        )

    @classmethod
    def generate_signature(cls, request):
        return hmac.new(
            settings.DROPBOX_APP_SECRET.encode('utf-8'),
            request.body,
            sha256
        ).hexdigest()

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

class ShopifyInterface:
    import shopify

    def __init__(self):
        "setup connection to Shopify"
        self.shopify.ShopifyResource.set_site(settings.SHOPIFY_SHOP_URL)
        self._get_products_from_shopify()

    def add_product(self, product):
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
        pprint(shop_product.variants[0].to_dict())
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

        pprint(shop_product.to_dict())

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

