import re, pytz, logging
from django.db import models
from interfaces import DropboxInterface
from core.models import Company

log = logging.getLogger('django')

dropbox = DropboxInterface()

class ExportType(models.Model):
    name = models.CharField(unique=True, max_length=64)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)

    def __str__(self):
        return '{}'.format(self.name)


class ImportFile(models.Model):
    class Meta:
        get_latest_by = 'server_modified'

    # Import Statuses
    IMPORTED = 'IMPORTED' # Data was imported to local database/cache
    IN_PROGRESS = 'IN_PROGRESS' # In process of importing
    NOT_IMPORTED = 'NOT_IMPORTED' # Default state
    EXPIRED = 'EXPIRED' # Never imported, other, newer file of same company/type exists
    IMPORT_STATUS_CHOICES = ((IMPORTED, 'Imported'),
                             (IN_PROGRESS, 'In Progress'),
                             (NOT_IMPORTED, 'Not Imported'),
                             (EXPIRED, 'Expired'),)

    type_company_pattern = re.compile(
        r'^\d{14}\.SHPFY_([A-Za-z]+)Extract_([A-Za-z]+)\.(?i)CSV$')

    dropbox_id = models.CharField(unique=True, max_length=64)
    path_lower = models.CharField(max_length=1024)
    filename = models.CharField(max_length=1024)
    server_modified = models.DateTimeField()
    company = models.ForeignKey(Company, on_delete = models.CASCADE)
    export_type = models.ForeignKey(ExportType, on_delete = models.CASCADE)
    import_status = models.CharField(max_length=16,
                                     choices=IMPORT_STATUS_CHOICES,
                                     default=NOT_IMPORTED)

    @classmethod
    def parse_company_export_type(cls, filename):
        """Parse the company and export_type from filename.
        """
        match = cls.type_company_pattern.match(filename)
        if match:
            company = match.group(2)
            export_type = match.group(1)
            return (company, export_type)
        else:
            raise ValueError(
                'Company or export type not found in filename: {}'
                .format(filename))

    @property
    def content(self):
        try:
            return dropbox.get_file_contents(self.dropbox_id)
        except Exception as e:
            log.exception(e)
            return None

    def __str__(self):
        return self.filename

    def __repr__(self):
        return '{}(path_lower={}, id={})'.format(
            self.__class__.__name__,
            self.path_lower,
            self.dropbox_id)
