from django.core.management.base import BaseCommand, CommandError

from data_import.controllers import Controller

class Command(BaseCommand):
    help = 'import the most recent product export files into the local database.'

    def add_arguments(self, parser):
        parser.add_argument('company_names', nargs='+', type=str)

    def handle(self, *args, **options):
        print(options['company_names'])
        Controller().import_latest_data(options['company_names'])
        pass

