from django.apps import AppConfig
from webhook import register_webhook

class DataImportConfig(AppConfig):
    name = 'data_import'

    # def ready(self):
    #     # register webhook
    #     from .views import verify_webhook, process_notification
    #     register_webhook(
    #         'dropbox-updated',
    #         {
    #             'GET': verify_webhook,
    #             'POST': process_notification,
    #         })
