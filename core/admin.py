import logging

from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.html import format_html

from .models import Company, FulfillmentService
from interfaces import ShopifyInterface


log = logging.getLogger('development')
current_app_name = __package__.rsplit('.', 1)[-1]


class FulfillmentServiceInline(admin.TabularInline):
    model = FulfillmentService
    extra = 0
    can_delete = False
    readonly_fields = ('location_id', 'handle', 'name',)
    list_display = ('is_import_destination', 'location_id',)

    def has_add_permission(self, request, obj):
        return False

    class Media:
        js = ('fulfillment_service_inline.js',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):

    # Prevent adding Companies manually. They should only be added when the
    # ImportFiles are created from the Dropbox files.
    def has_add_permission(self, request, obj=None):
        return False

    fields = ('name',
              'should_import',
              'shopify_shop_name',
              'shopify_api_key',
              'shopify_password',
              'shopify_url_is_valid',
              'shopify_actions',)
    list_display = ('name',
                    'shopify_shop_name',
                    'should_import',
                    'configured',
                    'import_fulfillment_service',
                    'shopify_actions',)
    readonly_fields = ('name',
                       'shopify_url_is_valid',
                       'shopify_actions',)

    # Returns HTML button(s) for shopify actions.
    def shopify_actions(self, obj):
        # only for Inventory files
        if not obj.shopify_url_is_valid:
            return None
        return format_html(
            '<a class="button" href="{}">Fetch Fulfillment Services</a>',
            reverse('admin:{}_fetch-fulfillment-services'.format(
                current_app_name),
                args=[obj.pk]))
    shopify_actions.short_description = 'Shopify Actions'

    inlines = [
        FulfillmentServiceInline,]

    def configured(self, obj):
        return obj.has_shop_url and obj.shopify_url_is_valid
    configured.boolean = True

    def import_fulfillment_service(self, obj):
        try:
            fulfillment_service = FulfillmentService.objects.get(
                company=obj,
                is_import_destination=True)
        except FulfillmentService.DoesNotExist:
            return None

        return fulfillment_service.name

    # URLs ####################################################################

    def get_urls(self):
        return [
            path(
                '<int:company_id>/fetch-fulfillment-services/',
                self.admin_site.admin_view(self.fetch_fulfillment_services),
                name='{}_fetch-fulfillment-services'.format(current_app_name),
            )
        ] + super().get_urls()

    # Views ###################################################################

    def fetch_fulfillment_services(self, request, company_id):
        has_error = False

        company = Company.objects.get(pk=company_id)

        if company.has_shop_url and company.shopify_url_is_valid:
            shop = ShopifyInterface(company.shop_url)

            for service_id, service in shop.fulfillment_services.items():
                # create the service in the db
                try:
                    self._create_fulfillment_service(
                        company,
                        service,
                        len(shop.fulfillment_services) == 1)
                except Exception as e:
                    has_error = True

        if has_error:
            self.message_user(
                request,
                'There was an error fetching Fulfillment Services from Shopfiy'
                'Please try again, but if the error persists notify the admin.',
                messages.ERROR)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    def _create_fulfillment_service(self, company, service,
                                    is_import_destination):
        # Get or create the company object for this import file
        service_args = {
            'company': company,
            'service_id': service.id,
            'location_id': service.location_id,
            'handle': service.handle,
            'name': service.name,
            'is_import_destination': is_import_destination}

        try:
            db_service, created = FulfillmentService.objects.get_or_create(
                **service_args)
        except Exception as e:
            # TODO: Send exception to admins via email
            log.error(
                'Could not get or create FulfilmentService with name "{}" from db'
                .format(service.name), exc_info=True)
            raise

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.shopify_url_is_valid:
            self.message_user(request, 'Shopify API settings are invalid', messages.WARNING)

