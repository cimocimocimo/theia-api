from django.contrib import admin

from .models import Color, ColorNameCorrection, Size, Product, Variant

# Register your models here.
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('momentis_name',
                    'name',
                    'code',
                    'is_correct',
                    'correction')
    list_editable = ('is_correct',
                     'correction')
    search_fields = ['momentis_name',
                    'name',
                    'code']
    readonly_fields = ('momentis_name',
                    'code')

@admin.register(ColorNameCorrection)
class ColorNameCorrectionAdmin(admin.ModelAdmin):
    pass

@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    pass

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    pass
