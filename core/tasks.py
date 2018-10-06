import logging, time
from celery import shared_task
from celery.signals import worker_ready, worker_shutdown
from pprint import pprint, pformat
from dropbox_import.models import ImportFile, ImportJob, ImportJobLogEntry

log = logging.getLogger('development')

@shared_task(bind=True)
def export_to_shopify(self, import_job_id):
    log.debug(
        'export_to_shopify(import_job_id={})'.format(import_job_id))

    job = ImportJob.objects.get(pk=import_job_id)

    log.debug('import filename: {}'.format(job.import_file.filename))

    # slep for 30 seconds
    time.sleep(5)

    raise Exception('just a test exception')

    return True
