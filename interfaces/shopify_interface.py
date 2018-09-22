import logging, shopify
from pprint import pprint, pformat

log = logging.getLogger('django')

class ShopifyInterface:
    # TODO: Remove coupling with Company model. Passing in a shop_url should be
    # enough.
    def __init__(self, company=None, shop_url=None):
        """setup connection to Shopify"""

        log.debug('Init ShopifyInterface')

        # Setup API client
        if company and not shop_url:
            self.shop_url = company.shop_url
        elif shop_url:
            self.shop_url = shop_url

        shopify.ShopifyResource.set_site(shop_url)

        self.company = company
        self.products = False
        self.variants = False
        self.locations = False
        self.fulfillment_services = False
        self.inventory_items = False
        self.inventory_levels = False

    @property
    def products(self):
        if not self.__products:
            self.__products = self._get_from_shopify(shopify.Product)
        return self.__products

    @products.setter
    def products(self, value):
        self.__products = value

    @property
    def variants(self):
        if not self.__variants:
            self.__variants = self._get_from_shopify(shopify.Variant)
        return self.__variants

    @variants.setter
    def variants(self, value):
        self.__variants = value

    @property
    def locations(self):
        if not self.__locations:
            self.__locations = self._get_from_shopify(shopify.Location)
        return self.__locations

    @locations.setter
    def locations(self, value):
        self.__locations = value

    @property
    def fulfillment_services(self):
        if not self.__fulfillment_services:
            self.__fulfillment_services = self._get_from_shopify(
                shopify.FulfillmentService,
                scope='all')
        return self.__fulfillment_services

    @fulfillment_services.setter
    def fulfillment_services(self, value):
        self.__fulfillment_services = value

    @property
    def inventory_levels(self):
        if not self.__inventory_levels:
            # join location ids into a string to pass to the find method
            location_ids_string = ','.join([str(id) for id in self.locations])
            # get the inventory levels for all locations
            inv_levels = self._get_all_paged(
                shopify.InventoryLevel.find,
                location_ids=location_ids_string)
            # save the inventory levels
            self.__inventory_levels = {
                # Use tuple as key with locaction_id and inventory_item_id since
                # InventoryLevels don't have their own id attribute.
                (x.location_id, x.inventory_item_id) : x
                for x in inv_levels }
        return self.__inventory_levels

    @inventory_levels.setter
    def inventory_levels(self, value):
        self.__inventory_levels = value

    def reset_inventory(self, location=None):
        for key, level in self.inventory_levels.items():
            # skip if a location instance was passed and its id does not match
            # the location_id of the current level.
            if location and location.id != level.location_id:
                continue
            if isinstance(level.available, int) and level.available > 0:
                self._set_inventory_level(level, 0)

    def update_product(self, pid, attr, value):
        prod = self.products[pid]
        # only update product if values don't match
        if getattr(prod, attr) != value:
            # Since we are updating the property of an object we don't need to
            # save the object back to the dict. The value is updated by
            # reference.
            setattr(prod, attr, value)
            prod.save()

    def set_level_available(self, location_id, inventory_item_id, available):
        shopify.InventoryLevel.set(
            location_id=location_id,
            inventory_item_id=inventory_item_id,
            available=available)

    def get_level_available(self, location_id, variant_id):
        level = self.inventory_levels[(location_id, variant_id)]
        if not isinstance(level, shopify.InventoryLevel):
            return None
        else:
            return level.available

    def _set_inventory_level(self, level, available):
        shopify.InventoryLevel.set(
            location_id=level.location_id,
            inventory_item_id=level.inventory_item_id,
            available=available)
    
    def _get_from_shopify(self, shopify_class, **kwargs):
        return {
            x.id:x
            for x in self._get_all_paged(
                    shopify_class.find, **kwargs)}

    @property
    def can_connect_to_shopify(self):
        # test to ensure shop_url is valid
        try:
            # Returns the Shop data. Simple and quick way to test.
            shopify.Shop.current()
            return True
        except Exception as e:
            log.error('shop_url is invalid')
            return False

    # TODO: Remove this method
    def get_products(self):
        return self.products

    def _get_all_paged(self, page_cb, limit=250, page_numb=1, **kwargs):
        items = []
        has_more = True
        while has_more:
            page = page_cb(
                limit=limit,
                page=page_numb,
                **kwargs
            )
            has_more = len(page) == limit
            page_numb += 1
            items.extend(page)
        return items
