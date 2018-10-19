from django.core.management.base import BaseCommand, CommandError

from pprint import pprint

from core.models import Company
from core.controllers import Controller

class Command(BaseCommand):
    help = 'Provides interface to Shopify products and inventory.'

    def add_arguments(self, parser):

        # parse subcommand
        parser.add_argument(
            'subcommand',
            choices=['reset-inventory',])

    def handle(self, *args, **options):

        # Get required arg 'subcommand'.
        subcommand = options['subcommand']

        companies = [ c for c in Company.objects.all() if c.has_shop_url]

        if len(companies) == 0:
            self.stderr.write(
                self.style.ERROR(
                    'No companies have been configured with Shopify credentials.'))

        if subcommand == 'reset-inventory':
            self.stdout.write('Choose a company to reset inventory in shopfy.', ending='\n\n')

            for i, c in enumerate(companies):
                self.stdout.write('{}. {} - {}'.format(i+1, c.name, c.shop_url))

            self.stdout.write('')

            choice = input('Enter number of company: ')

            self.stdout.write('')

            try:
                company = companies[int(choice) - 1]
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        'Choice {} is invalid'.format(choice)))
                return

            self.stdout.write(
                'Are you sure you want to reset inventory for {}?'
                .format(company.name))

            choice = input('y/N: ')

            try:
                if choice.lower() == 'y':
                    self.stdout.write(
                        'Resetting inventory for {}.'.format(company.name))

                    # reset store inventory to 0
                    Controller().reset_inventory(company)

                    self.stdout.write(
                        'Completed inventory reset of company {}.'.format(
                            company.name))

            except Exception as e:
                self.stderr.write(
                    'NOT resetting inventory, exiting.')
                raise
