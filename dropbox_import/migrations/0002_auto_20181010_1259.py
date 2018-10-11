# Generated by Django 2.1.1 on 2018-10-10 19:59

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('dropbox_import', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('NOT_STARTED', 'Not Started'), ('RUNNING', 'Running'), ('SUCCESS', 'Completed Successfully'), ('ERROR', 'Error - Not Completed')], default='NOT_STARTED', max_length=16)),
                ('celery_task_id', models.CharField(max_length=50, null=True, unique=True)),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Started')),
                ('end_time', models.DateTimeField(null=True, verbose_name='Finished')),
            ],
            options={
                'ordering': ('-start_time',),
            },
        ),
        migrations.CreateModel(
            name='ImportJobLogEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')], default='INFO', max_length=16)),
                ('message', models.TextField()),
                ('entry_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('import_job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dropbox_import.ImportJob')),
            ],
            options={
                'verbose_name': 'Log Entry',
                'verbose_name_plural': 'Log Entries',
            },
        ),
        migrations.AlterField(
            model_name='importfile',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.Company'),
        ),
        migrations.AddField(
            model_name='importjob',
            name='import_file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dropbox_import.ImportFile'),
        ),
    ]