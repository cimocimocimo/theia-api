from django.contrib import admin
from .models import Company, FulfillmentService

class FulfillmentServiceInline(admin.TabularInline):
    model = FulfillmentService
    extra = 0
    can_delete = False
    readonly_fields = ('location_id', 'handle', 'name',)
    list_display = ('is_import_destination', 'location_id',)

    def has_add_permission(request, obj):
        return False

    class Media:
        js = ('fulfillment_service_inline.js',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'shopify_shop_name',
                    'should_import',
                    'configured',
                    'import_fulfillment_service',)
    inlines = [
        FulfillmentServiceInline,]

    def configured(self, obj):
        return obj.has_shop_url
    configured.boolean = True

    def import_fulfillment_service(self, obj):
        try:
            fulfillment_service = FulfillmentService.objects.get(
                company=obj,
                is_import_destination=True)
        except FulfillmentService.DoesNotExist:
            return None

        return fulfillment_service.name
