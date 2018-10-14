from django.contrib import admin

from .models import DBLogEntry


@admin.register(DBLogEntry)
class DBLogEntryAdmin(admin.ModelAdmin):
    pass
