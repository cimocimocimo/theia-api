from django.apps import AppConfig
from webhook import register_webhook

class DataImportConfig(AppConfig):
    name = 'data_import'

    def ready(self):
        # register webhook
        from .interfaces import DropboxInterface
        register_webhook(
            'dropbox-updated',
            {
                'GET': DropboxInterface.verify_webhook,
                'POST': DropboxInterface.process_notification,
            })
