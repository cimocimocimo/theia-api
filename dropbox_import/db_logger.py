from .models.import_job_log_entry import ImportJobLogEntry


class DBLogger:

    def __init__(self, import_job=None):
        self.import_job = import_job

    def info(self, message):
        self._log(message=message)

    def warning(self, message):
        self._log(level=ImportJobLogEntry.WARNING, message=message)

    def error(self, message):
        self._log(level=ImportJobLogEntry.ERROR, message=message)

    def _log(self, message, level=ImportJobLogEntry.INFO):
        ImportJobLogEntry.objects.create(
            level=level,
            message=message,
            import_job=self.import_job,)
