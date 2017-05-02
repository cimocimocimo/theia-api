from django.contrib import admin

from .models import Color, ColorNameCorrection, Size, Product, Variant, Company

# Register your models here.
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('momentis_name',
                    'name',
                    'code',
                    'is_correct',
                    'correction',)
    list_editable = ('is_correct',
                     'correction',)
    search_fields = ['momentis_name',
                     'name',
                     'code',]
    readonly_fields = ('momentis_name',
                       'code',)

@admin.register(ColorNameCorrection)
class ColorNameCorrectionAdmin(admin.ModelAdmin):
    pass

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    pass

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('style_number',
                    'name',
                    'category',
                    'division',)
    list_filter = ('division',
                   'category',)
    search_fields = ['style_number',
                     'name',
                     'description',
                     'division',]

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    pass

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # Company name should not be editable
    readonly_fields = ('name',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

