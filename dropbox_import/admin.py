import logging, dropbox, pytz
from django.contrib import admin
from django.urls import include, path, reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from pprint import pprint, pformat
from .models import ImportFile, ExportType
from core.models import Company
from interfaces import DropboxInterface

from django.utils.timezone import make_aware

log = logging.getLogger('development')
dropbox_interface = DropboxInterface()
current_app_name = __package__.rsplit('.', 1)[-1]

@admin.register(ImportFile)
class ImportFileAdmin(admin.ModelAdmin):

    # Prevent adding or deleting ImportFiles manually.
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    # Fields to show on the list/change view of the admin
    list_display = readonly_fields = (
        'filename',
        'server_modified',
        'company',
        'export_type',
        'import_status',
        'file_actions', # Renders buttons to trigger actions, defined below.
    )
    # Set 2 additional fields as read only.
    readonly_fields = readonly_fields + ('dropbox_id', 'path_lower')

    # Adds button to list page for populating the Import Files from Dropbox.
    change_list_template = 'admin/import_file_change_list.html'

    # Returns html button for file actions.
    def file_actions(self, obj):
        # only for Inventory files
        if obj.export_type.name != 'Inventory':
            return None
        return format_html(
            '<a class="button" href="{}">Process File</a>',
            reverse('admin:{}_process-import-file'.format(current_app_name),
                    args=[obj.pk]))
    file_actions.short_description = 'Actions'

    # Add urls and bind their actions to methods defined below.
    def get_urls(self):
        return [
            path(
                'load/',
                self.admin_site.admin_view(self.load_import_files),
                name='{}_load-import-files'.format(current_app_name),
            ),
            path(
                '<int:import_file_id>/process/',
                self.admin_site.admin_view(self.process_import_file),
                name='{}_process-import-file'.format(current_app_name),
            ),
        ] + super().get_urls()

    def process_import_file(self, request, import_file_id):
        try:
            redirect_url = request.META['HTTP_REFERER']
        except (AttributeError, KeyError,) as e:
            log.error('Direct call to process_import_file() is not allowed.')
            log.exception(e)
            return

        try:
            file = ImportFile.objects.get(pk=import_file_id)
        except ImportFile.DoesNotExist:
            log.error(
                'Import file with pk={} not found.'.format(import_file_id))
            return

        self.message_user(
            request,
            'I didnt load shit..., but I should have loaded file_id {}'
            'moreo f the message'
            .format(import_file_id))
        return HttpResponseRedirect(redirect_url)

    def load_import_files(self, request):
        # list all files in the dropbox export folder
        entries = dropbox_interface.list_all_files()

        # make sure we have some files to import
        if entries == None:
            self.message_user(
                request,
                'No data files found in dropbox folder {}.'.format(
                settings.DROPBOX_EXPORT_FOLDER))
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
        return HttpResponseRedirect("../")

