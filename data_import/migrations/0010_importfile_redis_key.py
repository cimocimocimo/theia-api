# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-01-05 22:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_import', '0009_auto_20170103_2137'),
    ]

    operations = [
        migrations.AddField(
            model_name='importfile',
            name='redis_key',
            field=models.CharField(max_length=1024, null=True),
        ),
    ]
