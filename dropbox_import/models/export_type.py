import logging

from django.db import models


log = logging.getLogger('django')


class ExportType(models.Model):
    name = models.CharField(unique=True, max_length=64)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)

    def __str__(self):
        return '{}'.format(self.name)

