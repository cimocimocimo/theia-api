from django.test import TestCase
from django.utils import timezone
from core.celery import test_task
from .models import ImportFile, ExportType, ImportJob

class ImportFileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_type = ExportType.objects.create(name='TestingExportType')
        pass

    def create_file(self):
        """Create and return a testing file.
        """
        return ImportFile.objects.create(dropbox_id='testfile',
                                         path_lower='testfile',
                                         filename='TestFile',
                                         server_modified=timezone.now(),
                                         export_type=self.export_type,)

    def test_init(self):
        pass

    def test_start_task(self):
        file = self.create_file()
        file.start_job_task(
            job_task=test_task,
            extra={'sleep_time': 5},)
        # get job
        job = ImportJob.objects.get(import_file=file)
        self.assertIsInstance(job, ImportJob)
        self.assertEqual(job.status, ImportJob.RUNNING)
        self.assertIsNotNone(job.celery_task_id)

    def test_start_task_error(self):
        file = self.create_file()
        # get job
        try:
            # will trigger error for the test
            file.start_job_task(job_task=None)
        except:
            pass
        job = ImportJob.objects.get(import_file=file)
        self.assertIsInstance(job, ImportJob)
        self.assertEqual(job.status, ImportJob.ERROR)
        self.assertIsNone(job.celery_task_id)

    def test_is_importing(self):
        file = self.create_file()
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
    def test_long_name(self):
        pass
