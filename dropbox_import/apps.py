from django.apps import AppConfig
from webhook import register_webhook

class DropboxImportConfig(AppConfig):
    name = 'dropbox_import'

    def ready(self):
        # register webhook
        from .views import verify_webhook, process_webhook_notification
        register_webhook(
            'dropbox-updated',
            {
                'GET': verify_webhook,
                'POST': process_webhook_notification,
            })
