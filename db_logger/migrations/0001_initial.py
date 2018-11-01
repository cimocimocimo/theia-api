# Generated by Django 2.1.1 on 2018-10-13 08:53

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dropbox_import', '0002_auto_20181013_1826'),
    ]

    operations = [
        migrations.CreateModel(
            name='DBLogEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')], default='INFO', max_length=16)),
                ('message', models.TextField()),
                ('entry_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('import_job', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='dropbox_import.ImportJob')),
            ],
            options={
                'verbose_name': 'Log Entry',
                'verbose_name_plural': 'Log Entries',
            },
        ),
    ]
