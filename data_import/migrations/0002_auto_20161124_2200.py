# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-24 22:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_import', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='style_number',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
