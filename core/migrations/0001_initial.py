# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2018-08-13 00:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
                ('should_import', models.BooleanField(default=False)),
                ('shopify_shop_name', models.CharField(blank=True, max_length=256, null=True, unique=True)),
                ('shopify_api_key', models.CharField(blank=True, max_length=256, null=True)),
                ('shopify_password', models.CharField(blank=True, max_length=256, null=True)),
            ],
        ),
    ]