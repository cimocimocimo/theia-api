import logging
from pprint import pprint, pformat

from celery import shared_task
from django.db import models
from django.utils import timezone

from ..db_logger import DBLogger


log = logging.getLogger('django')


class ImportJob(models.Model):
    # Import Statuses
    NOT_STARTED = 'NOT_STARTED'
    RUNNING = 'RUNNING'
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    STATUS_CHOICES = ((NOT_STARTED, 'Not Started'),
                      (RUNNING, 'Running'),
                      (SUCCESS, 'Completed Successfully'),
                      (ERROR, 'Error - Not Completed'),)

    status = models.CharField(max_length=16,
                              choices=STATUS_CHOICES,
                              default=NOT_STARTED)
    import_file = models.ForeignKey('dropbox_import.ImportFile', on_delete = models.CASCADE)
    celery_task_id = models.CharField(max_length = 50, unique=True, null=True)
    start_time = models.DateTimeField(default=timezone.now, verbose_name='Started')
    end_time = models.DateTimeField(null=True, verbose_name='Finished')

    class Meta:
        ordering = ('-start_time',)

    def start(self, job_task=None, extra={}):
        # Format the keyword args for the celery tasks
        task_kwargs = {
            'import_job_id': self.pk,
            # merge in additional kwargs
            **extra,}

        try:
            task = job_task.apply_async(
                kwargs=task_kwargs,
                # success/error tasks defined below
                link=job_success.s(**task_kwargs),
                link_error=job_error.s(**task_kwargs),)
        except Exception as e:
            # mark job as failed and save.
            self.finish(err=True)
            raise

        # Task started successfully
        self.status = self.RUNNING
        self.celery_task_id = task.id
        self.save()
        DBLogger(import_job=self).info('Task started successfully.')
        return self

    def finish(self, err=False):
        if err:
            self.status = self.ERROR
        else:
            self.status = self.SUCCESS
        self.end_time = timezone.now()
        self.save()

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__, self.pk)

    def __str__(self):
        return 'pk:{}, {}'.format(
            self.pk, self.start_time.strftime('%Y-%m-%d %H:%M'))


# Success/Error Tasks for the ImportJobs
@shared_task(bind=True)
def job_success(self, return_value, *args,
                import_file_id=None, import_job_id=None, **kwargs):
    print('linked success')
    print(locals())
    # Mark ImportJob as success
    job = ImportJob.objects.get(pk=import_job_id)
    DBLogger(import_job=job).info('Job completed successfully.')
    job.finish()
    pass

@shared_task(bind=True)
def job_error(self, *args,
              import_file_id=None, import_job_id=None, **kwargs):
    print('linked error')
    print(locals())
    # Mark ImportJob as success
    job = ImportJob.objects.get(pk=import_job_id)
    DBLogger(import_job=job).error('Error occurred processing job.')
    job.finish(err=True)
    pass
