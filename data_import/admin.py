from django.contrib import admin

from .models import Color, Size, Product, Variant

# Register your models here.
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
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
