import logging, pytz
from pprint import pprint, pformat

import dropbox
from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import messages
from django.utils.timezone import make_aware

from interfaces import DropboxInterface
from core.models import Company
from core.controllers import Controller
from .models import ImportFile, ExportType, ImportJob
from db_logger.models import DBLogEntry


log = logging.getLogger('development')
dropbox_interface = DropboxInterface()
current_app_name = __package__.rsplit('.', 1)[-1]
controller = Controller()


def check_referer(func):
    """Decorator for checking a request for a referer in custom admin views

    All admin views should have a referer to ensure that the request came from
    a user clicking on a button. Not a perfect check but, decent.
    """
    def _check_referer(obj, request, *args, **kwargs):
        try:
            request.META['HTTP_REFERER']
        except KeyError as e:
            message = 'Direct call to export_to_shopify() is not allowed.'
            obj.message_user(request, message, messages.WARNING)
            log.error(message)
            log.exception(e)
            return HttpResponseRedirect(
                reverse(
                    'admin:dropbox_import_importfile_changelist'))

        return func(obj, request, *args, **kwargs)
    return _check_referer

class ImportAdminBase(admin.ModelAdmin):

    # Prevent adding, changing, or deleting Model objects manually.
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False

    # Company link formatter
    def format_company_link(self, name, pk):
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                'admin:core_company_change',
                args=(pk,)),
            name,)


class ImportJobInline(admin.TabularInline):

    model = ImportJob
    show_change_link = True
    fields = (
        'status',
        'start_time',
        'end_time',)

    # Prevent adding, changing, or deleting Model objects manually.
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ImportFile)
class ImportFileAdmin(ImportAdminBase):

    fields = ('filename',
        'server_modified',
        'company_link',
        'export_type',
        'import_status',
        'file_actions', # Renders buttons to trigger actions, defined below.
    )
    # Fields to show on the list/change view of the admin
    list_display = (
        'filename',
        'server_modified',
        'company_link',
        'export_type',
        'import_status',
        'file_actions', # Renders buttons to trigger actions, defined below.
    )
    list_filter = (
        'company__name',
        'export_type__name',
        'server_modified',
    )

    # Adds button to list page for populating the Import Files from Dropbox.
    change_list_template = 'admin/import_file_change_list.html'

    def company_link(self, obj):
        return self.format_company_link(obj.company.name, obj.company.pk)
    company_link.short_description = 'Company'

    # Returns HTML button for file actions.
    def file_actions(self, obj):
        # only for Inventory files
        if obj.export_type.name != 'Inventory':
            return None
        if not obj.company.shopify_url_is_valid:
            return 'Shopify not configured'
            return None

        if obj.is_importing():
            return 'Import Job Running'

        return format_html(
            '<a class="button" href="{}">Export to Shopify</a>',
            reverse('admin:{}_export-shopify'.format(current_app_name),
                    args=[obj.pk]))
    file_actions.short_description = 'Actions'

    inlines = [
        ImportJobInline,]

    # URLs ####################################################################

    def get_urls(self):
        return [
            path(
                'load/',
                self.admin_site.admin_view(self.load_files),
                name='{}_load-files'.format(current_app_name),
            ),
            path(
                '<int:import_file_id>/export/',
                self.admin_site.admin_view(self.start_shopify_export),
                name='{}_export-shopify'.format(current_app_name),
            ),
        ] + super().get_urls()

    # Views ###################################################################

    @check_referer
    def start_shopify_export(self, request, import_file_id):
        """Handles the HTTP request and dispatches the controller action

        This handles the HTTP side of things and also catches exceptions and
        displays messages to the user.
        """

        # Default message type
        message_type = messages.INFO

        # User has clicked on the export to shopify button. We should have a
        # valid ImportFile id.
        try:
            message = controller.start_shopify_export(import_file_id)
        # Handle error conditions and notify the user
        except ImportFile.DoesNotExist as e:
            message = 'Import file with pk={} not found.'.format(
                import_file_id)
            message_type = messages.WARNING
            log.exception(e)
        except ValueError as e:
            message = e
            message_type = messages.WARNING
            log.exception(e)
        except Exception as e:
            message = e
            message_type = messages.ERROR
            log.exception(e)

        # Set user message and redirect.
        self.message_user(request, message, message_type)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    @check_referer
    def load_files(self, request):
        """Loads import files from Dropbox.
        """

        # TODO: Refactor this into the controller. Only keep logic related to
        # Admin UI.

        redirect_url = request.META['HTTP_REFERER']

        # list all files in the dropbox export folder
        entries = dropbox_interface.list_all_files()

        # make sure we have some files to import
        if entries == None:
            self.message_user(
                request,
                'No data files found in dropbox folder {}.'.format(
                    settings.DROPBOX_EXPORT_FOLDER),
                messages.WARNING)
            return HttpResponseRedirect("../")

        for filemeta in entries:
            log.debug(pformat(filemeta))

            # skip non-files
            if type(filemeta) != dropbox.files.FileMetadata:
                continue

            # get the company and export type
            try:
                company_name, export_type_name = ImportFile.parse_company_export_type(filemeta.name)
            except ValueError as e:
                # skip any files that don't have company and export types
                log.warning(e)
                continue

            try:
                company, created = Company.objects.get_or_create(
                    name=company_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                export_type, created = ExportType.objects.get_or_create(
                    name=export_type_name)
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

            try:
                import_file, created = ImportFile.objects.update_or_create(
                    dropbox_id=filemeta.id,
                    defaults={
                        'path_lower': filemeta.path_lower,
                        'filename': filemeta.name,
                        'server_modified': make_aware(filemeta.server_modified, timezone=pytz.UTC),
                        'company': company,
                        'export_type': export_type,})
            except ValueError as e:
                log.warning(e)
            except Exception as e:
                log.exception(e)
                return

        # delete ImportFiles from database that are not in dropbox

        # create a list of dropbox file ids
        entry_ids = [ e.id for e in entries]

        # loop over the files in the database, check each db file dropbox_id
        # if it is not in the list of dropbox file ids, then we delete it.
        ImportFile.objects.exclude(dropbox_id__in=entry_ids).delete()
        
        self.message_user(request, "Import Files have been loaded.")
        return HttpResponseRedirect(redirect_url)


class DBLogEntryInline(admin.TabularInline):

    model = DBLogEntry
    show_change_link = True
    fields = (
        'level',
        'entry_date',
        'message',)

    # Prevent adding, changing, or deleting Model objects manually.
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ImportJob)
class ImportJobAdmin(ImportAdminBase):

    def import_file_link(self, obj):
        url = reverse(
                'admin:dropbox_import_importfile_change',
                args=(obj.import_file.pk,))
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.import_file.filename,)
    import_file_link.short_description = 'Import File'
    import_file_link.admin_order_field = 'import_file__server_modified'
        
    def get_export_type(self, obj):
        return obj.import_file.export_type.name
    get_export_type.short_description = 'Export Type'
    get_export_type.admin_order_field = 'import_file__export_type'

    fields = (
        '__str__',
        'import_file_link',
        'company_link',
        'get_export_type',
        'status',
        'start_time',
        'end_time',)
    list_display = (
        '__str__',
        'import_file_link',
        'company_link',
        'get_export_type',
        'status',
        'start_time',
        'end_time',
    )
    list_filter = (
        'import_file__company__name',
        'import_file__export_type__name',
        'status',
        'start_time',
    )

    def company_link(self, obj):
        return self.format_company_link(obj.import_file.company.name,
                                        obj.import_file.company.pk)
    company_link.short_description = 'Company'

    inlines = [
        DBLogEntryInline,]
