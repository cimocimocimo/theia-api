from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import DBLogEntry


@admin.register(DBLogEntry)
class DBLogEntryAdmin(admin.ModelAdmin):

    # Prevent adding, changing, or deleting Model objects manually.
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    fields = (
        'level',
        'entry_date',
        'message',
        'import_job_link',)
    list_display = (
        '__str__',
        'level',
        'entry_date',
        'message',
        'import_job_link',)
    list_filter = (
        'level',
        'entry_date',)

    def import_job_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                'admin:dropbox_import_importjob_change',
                args=(obj.import_job.pk,)),
            obj.import_job,)
    import_job_link.short_description = 'Import Job'

