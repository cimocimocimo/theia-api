from django.core.management.base import BaseCommand, CommandError

from data_import.controllers import Controller

class Command(BaseCommand):
    help = 'import the most recent product export files into the local database.'

    def add_arguments(self, parser):

        # parse subcommand
        parser.add_argument(
            'subcommand',
            choices=['get_import_files', 'import', 'export', 'full', 'reset_import_files'])

        # 2nd is a flag and optional
        parser.add_argument(
            '-f',
            '--company_filter',
            nargs='+',
            type=str)

    def handle(self, *args, **options):

        controller = Controller()

        subcommand = None
        if 'subcommand' in options:
            subcommand = options['subcommand']

        company_filter = None
        if 'company_filter' in options:
            company_filter = options['company_filter']

        if subcommand == 'import':
            self.stdout.write('Importing data')
            controller.import_latest_data(company_filter)

        elif subcommand == 'export':
            self.stdout.write('Exporting data')
            controller.export_data(company_filter)

        elif subcommand == 'get_import_files':
            self.stdout.write('Getting import files')
            controller.get_import_files()

        elif subcommand == 'reset_import_files':
            self.stdout.write('Resetting import files')
            controller.reset_import_files()

        else:
            self.stdout.write('Running full data Import/Export')
            controller.full_import_export(company_filter)



