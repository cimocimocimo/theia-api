from django.contrib import admin

from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    pass

# @admin.register(Company)
# class CompanyAdmin(admin.ModelAdmin):
#     # Company name should not be editable
#     readonly_fields = ('name',)

#     def has_add_permission(self, request):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False
