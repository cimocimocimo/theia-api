import logging, re

from django.db import models

from core.models import Company
from ..models import ExportType, ImportJob


log = logging.getLogger('django')


class ImportFile(models.Model):
    class Meta:
        get_latest_by = 'server_modified'

    # Import Statuses
    # TODO: Are we using ImportFile.status? If not let's remove it.
    # TODO: If ImportFile.status is unused, replace with a property that checks
    # the status of the import jobs. Perhaps just the last one.
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
    company = models.ForeignKey(Company, null=True,
                                on_delete = models.SET_NULL)
    export_type = models.ForeignKey(ExportType, on_delete = models.CASCADE)
    import_status = models.CharField(max_length=16,
                                     choices=IMPORT_STATUS_CHOICES,
                                     default=NOT_IMPORTED)

    @property
    def content(self):
        try:
            return dropbox.get_file_contents(self.dropbox_id)
        except Exception as e:
            log.exception(e)
            return None

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

    def is_importing(self):
        # Get ImportJob instances for this ImportFile. There really should only
        # be one but we do it this way to avoid possible Exceptions.
        job_count = self.importjob_set.filter(
            status__in=[ImportJob.NOT_STARTED,
                    ImportJob.RUNNING,],
        ).count()
        # Return boolean
        return job_count > 0

    def __str__(self):
        return self.filename

    def __repr__(self):
        return '{}(path_lower={}, dropbox_id={})'.format(
            self.__class__.__name__,
            self.path_lower,
            self.dropbox_id)
