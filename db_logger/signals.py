from django.dispatch import receiver, Signal

# from dropbox_import.models import ImportJob
from .models import DBLogEntry


# Signals #####################################################################

providing_args = ['message',
                  'import_job_pk']

info = Signal(providing_args=providing_args)
warning = Signal(providing_args=providing_args)
error = Signal(providing_args=providing_args)


# Senders #####################################################################

class DBLogger:

    def info(self, message, import_job_pk):
        info.send(sender=self.__class__, message=message,
                  import_job_pk=import_job_pk)

    def warning(self, message, import_job_pk):
        warning.send(sender=self.__class__, message=message,
                     import_job_pk=import_job_pk)

    def error(self, message, import_job_pk):
        error.send(sender=self.__class__, message=message,
                   import_job_pk=import_job_pk)


# Receivers ###################################################################

@receiver(info)
def log_info(*args, **kwargs):
    _log(*args, **kwargs)

@receiver(warning)
def log_warning(*args, **kwargs):
    _log(*args, level=DBLogEntry.WARNING, **kwargs)

@receiver(error)
def log_error(*args, **kwargs):
    _log(*args, level=DBLogEntry.ERROR, **kwargs)

def _log(sender, message, *args,
         import_job_pk=None, level=DBLogEntry.INFO, **kwargs):

    entry = DBLogEntry(message=message, level=level)
    if import_job_pk:
        entry.import_job_id = import_job_pk
    entry.save()
