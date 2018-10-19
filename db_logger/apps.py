from django.apps import AppConfig


class DbLoggerConfig(AppConfig):
    name = 'db_logger'
    verbose_name = 'Database Log'

    def ready(self):
        import db_logger.signals # noqa
        pass
