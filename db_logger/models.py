import logging

from django.db import models
from django.utils import timezone


log = logging.getLogger('django')


class DBLogEntry(models.Model):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

    LEVEL_CHOICES = ((INFO, 'Info'),
                     (WARNING, 'Warning'),
                     (ERROR, 'Error'),)
    level = models.CharField(max_length=16,
                              choices=LEVEL_CHOICES,
                               default=INFO)
    message = models.TextField()
    entry_date = models.DateTimeField(default=timezone.now)
    import_job = models.ForeignKey('dropbox_import.ImportJob',
                                   on_delete = models.CASCADE,
                                   null=True)

    class Meta:
        verbose_name = 'Log Entry'
        verbose_name_plural = 'Log Entries'

    def __str__(self):
        truncate_length = 64
        message_truncated = False
        if len(self.message) > truncate_length:
            message_truncated = (self.message[:truncate_length] + '...')
        return '{} {}'.format(
            self.level,
            message_truncated or self.message)
