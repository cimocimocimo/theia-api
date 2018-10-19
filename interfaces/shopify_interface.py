import logging, shopify
from pprint import pprint, pformat


log = logging.getLogger('development')


class ShopifyInterface:

    def __init__(self, shop_url, fulfillment_service_id=None):
        """setup connection to Shopify"""
        log.debug('Init ShopifyInterface')

        # Setup API client
        self.shop_url = shop_url
        shopify.ShopifyResource.set_site(self.shop_url)

        # test to ensure shop_url is valid
        try:
            # Returns the Shop data. Simple and quick way to test.
            self.shop = shopify.Shop.current()
        except Exception as e:
            raise
        else:
            self.can_connect = True

        self.products = False
        self.variants = False
        self.fulfillment_services = False
        self.inventory_items = False
        self.inventory_levels = False
        # set default fulfilment service
        if fulfillment_service_id:
            self.set_default_fulfillment(fulfillment_service_id)
        else:
            self.default_fulfillment = False

    def set_default_fulfillment(self, service_id):
        self.default_fulfillment = self.fulfillment_services[service_id]

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
            self.__variants = {
                v.id:v
                for v in self._get_all_paged(
                        shopify.Variant.find)
                if v.fulfillment_service == self.default_fulfillment.handle}
        return self.__variants

    @variants.setter
    def variants(self, value):
        self.__variants = value

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
        if not self.default_fulfillment:
            raise ValueError('FulfillmentService needs to be set.')
        if not self.__inventory_levels:
            self.__inventory_levels = {
                x.inventory_item_id:x
                for x in self._get_all_paged(
                        shopify.InventoryLevel.find,
                        location_ids=self.default_fulfillment.location_id)}
        return self.__inventory_levels

    @inventory_levels.setter
    def inventory_levels(self, value):
        self.__inventory_levels = value

    def reset_inventory(self):
        log.debug('Resetting Inventory')
        for key, variant in self.variants.items():
            self.set_level_available(variant, 0)

    def update_product(self, product, attr, value):
        # only update product if values don't match
        if getattr(product, attr) != value:
            setattr(product, attr, value)
            product.save()
            self.products[product.id] = product

    def get_level_available(self, variant):
        level = self.inventory_levels[variant.inventory_item_id]
        try:
            return level.available
        except Exception as e:
            log.exception(e)
            return None

    def set_level_available(self, variant, available):
        key = variant.inventory_item_id
        try:
            level = self.inventory_levels[key]
        except KeyError as e:
            log.exception(e)
            log.debug(pformat(variant.to_dict()))

        # Only update if the available amounts are different.
        if level.available == available:
            return level

        new_level = shopify.InventoryLevel.set(
            location_id=self.default_fulfillment.location_id,
            inventory_item_id=key,
            # We're using a fulfillment service so we can only have one
            # location for each inventory_level
            # https://help.shopify.com/en/api/reference/inventory/inventorylevel#inventory-levels-and-fulfillment-service-locations
            disconnect_if_necessary=True,
            available=available)

        # save the updated level
        self.inventory_levels[key] = new_level
        return new_level

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
