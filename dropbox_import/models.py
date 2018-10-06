import re, pytz, logging
from pprint import pprint, pformat
from celery import shared_task
from django.db import models
from django.utils import timezone
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
        job_count = ImportJob.objects.filter(
            import_file=self,
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

    def start_job_task(self, job_task=None, extra={}):
        # Create an ImportJob for this file
        job = ImportJob.objects.create(import_file=self)
        job.job_task = job_task
        # try to start celery task
        job.start(job_task=job_task, extra=extra)
        return job

class ImportJob(models.Model):
    # Import Statuses
    NOT_STARTED = 'NOT_STARTED'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    STATUS_CHOICES = ((NOT_STARTED, 'Celery Task Not Started'),
                      (RUNNING, 'Celery Task Running'),
                      (SUCCESS, 'Job Completed Successfully'),
                      (ERROR, 'Job Completed with Errors'),)

    status = models.CharField(max_length=16,
                              choices=STATUS_CHOICES,
                              default=NOT_STARTED)
    import_file = models.ForeignKey(ImportFile, on_delete = models.CASCADE)
    celery_task_id = models.CharField(max_length = 50, unique=True, null=True)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True)

    def start(self, job_task, extra={}):
        # Format the keyword args for the celery tasks
        task_kwargs = {
            'import_job_id': self.pk,
            # merge in additional kwargs
            **extra,}

        try:
            task = self.job_task.apply_async(
                kwargs=task_kwargs,
                # success/error tasks defined below
                link=job_success.s(**task_kwargs),
                link_error=job_error.s(**task_kwargs),)
        except Exception as e:
            # mark job as failed and save.
            self.finish(err=True)
            raise

        # Task started successfully
        self.status = ImportJob.RUNNING
        self.celery_task_id = task.id
        self.save()
        return self

    def finish(self, err=False):
        if err:
            self.status = ImportJob.ERROR
        else:
            self.status = ImportJob.SUCCESS
        self.end_time = timezone.now()
        self.save()

    # def __init__(self, *args, import_file, job_task, **kwargs):
    #     super().__init__(import_file, *args, **kwargs)

# Success/Error Tasks for the ImportJobs
@shared_task(bind=True)
def job_success(self, return_value, *args,
                import_file_id=None, import_job_id=None, **kwargs):
    print('linked success')
    pprint(locals())
    # Mark ImportJob as success
    job = ImportJob.objects.get(pk=import_job_id)
    job.finish()
    pass

@shared_task(bind=True)
def job_error(self, *args,
              import_file_id=None, import_job_id=None, **kwargs):
    print('linked error')
    pprint(locals())
    # Mark ImportJob as success
    job = ImportJob.objects.get(pk=import_job_id)
    job.finish(err=True)
    pass

class ImportJobLogEntry(models.Model):
    # levels = (DEBUG,
    #           INFO,
    #           WARNING,
    #           ERROR,
    #           CRITICAL,)



    import_job = models.ForeignKey(ImportJob, on_delete = models.CASCADE)
    pass

