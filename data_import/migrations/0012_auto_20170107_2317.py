# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-01-07 23:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_import', '0011_auto_20170106_2211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='color',
            name='code',
            field=models.CharField(max_length=8, unique=True),
        ),
    ]
