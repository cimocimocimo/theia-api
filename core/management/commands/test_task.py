from django.core.management.base import BaseCommand
from core.tasks import add

class Command(BaseCommand):
    def handle(self, *args, **options):
        print(add.delay(2,2).get())
