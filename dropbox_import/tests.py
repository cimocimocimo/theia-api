from django.test import TestCase
from django.utils import timezone
from core.celery import test_task
from .models import ImportFile, ExportType, ImportJob, ImportJobLogEntry
from .db_logger import DBLogger


def create_file(export_type):
    """Create and return a testing file.
    """
    return ImportFile.objects.create(
        dropbox_id='testfile',
        path_lower='testfile',
        filename='TestFile',
        server_modified=timezone.now(),
        export_type=export_type,)


def create_import_job(import_file):
    return ImportJob.objects.create(
        import_file=import_file,)


class ImportFileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_type = ExportType.objects.create(name='TestingExportType')

    def test_init(self):
        pass

    def test_is_importing(self):
        file = create_file(self.export_type)
        # default should just return false
        self.assertFalse(file.is_importing())
        # create ImportJob
        job = ImportJob(import_file=file)
        job.status = ImportJob.NOT_STARTED
        job.save()
        self.assertTrue(file.is_importing())
        job.status = ImportJob.RUNNING
        job.save()
        self.assertTrue(file.is_importing())

class ImportJobTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.export_type = ExportType.objects.create(name='TestingExportType')

    def test_start(self):
        file = create_file(self.export_type)
        job = create_import_job(import_file=file)
        job.start(
            job_task=test_task,
            extra={'sleep_time': 5},)
        self.assertEqual(job.status, ImportJob.RUNNING)
        self.assertIsNotNone(job.celery_task_id)
        
    def test_start_error(self):
        file = create_file(self.export_type)
        job = create_import_job(import_file=file)
        try:
            # will trigger error for the test
            job.start(job_task=None)
        except:
            pass
        self.assertEqual(job.status, ImportJob.ERROR)
        self.assertIsNone(job.celery_task_id)


class DBLoggerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.export_type = ExportType.objects.create(name='TestingExportType')

    def test_init(self):
        file = create_file(export_type=self.export_type)
        job = create_import_job(import_file=file)
        db_log = DBLogger(import_job=job)
        db_log.info('hello world')

        entry = ImportJobLogEntry.objects.get(import_job=job.pk)
        self.assertEqual('hello world', entry.message)
        self.assertEqual(ImportJobLogEntry.INFO, entry.level)
