from django.contrib import admin

from .models import Company, Location
from django.utils.html import format_html

class LocationInline(admin.TabularInline):
    model = Location
    extra = 0
    can_delete = False
    readonly_fields = ('shopify_id', 'is_legacy', 'name',)
    list_display = ('is_import_destination', 'shopify_id', 'is_legacy',)

    def has_add_permission(request, obj):
        return False


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'shopify_shop_name',
                    'should_import',
                    'configured',
                    'import_location',)
    inlines = [
        LocationInline,]

    def configured(self, obj):
        return obj.has_shop_url
    configured.boolean = True

    def import_location(slef, obj):
        try:
            loc = Location.objects.get(company=obj, is_import_destination=True)
        except Location.DoesNotExist:
            return None

        return loc.name

# @admin.register(Company)
# class CompanyAdmin(admin.ModelAdmin):
#     # Company name should not be editable
#     readonly_fields = ('name',)

#     def has_add_permission(self, request):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False
