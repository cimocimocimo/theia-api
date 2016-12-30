from django.test import TestCase
from django.conf import settings

from ..interfaces import DropboxInterface
from ..models import Product, Variant, ImportFileMeta, ImportFileMetaSet

class DropboxInterfaceTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dropbox_interface = DropboxInterface()

        super().setUpClass()

    def test_list_files(self):
        files = self.dropbox_interface.list_files(
            account=None,
            path=settings.DROPBOX_EXPORT_FOLDER)

        import_file_set = ImportFileMetaSet([
            ImportFileMeta(e) for e in files
            if ImportFileMeta.is_import_filemeta(e)
        ])

        import_files = import_file_set.get_import_files()

        for k, v in import_files.items():
            
