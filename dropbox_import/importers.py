import logging, re

from core.models import Inventory


log = logging.getLogger('development')


"""
These import the Product and Inventory CSV files
This should take the text of the body of the csv file downloaded
clean it up, remove the extra comma
then process all the lines of that file to create the needed objects
"""

class ImporterBase:
    def __init__(self, company=None, rows=None):
        self.rows = rows
        self.company = company

    def pre_import_data(self):
        pass

    def import_data(self):
        self.pre_import_data()

        for row in self.rows:
            self.process_row(row)

        self.post_import_data()

    def post_import_data(self):
        pass

    def process_row(self, row):
        pass


class InventoryImporter(ImporterBase):
    """
    Import the inventory to redis

    set of the UPCS

    hash of each data line keyed by UPC
    """

    missing_upcs = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inventory = Inventory(self.company.name)

    def pre_import_data(self):
        self.inventory.reset()
        super().pre_import_data()

    def import_data(self, *args, **kwargs):
        super().import_data(*args, **kwargs)

    def post_import_data(self):
        super().post_import_data()

    def process_row(self, row):
        upc = row['UPC']

        # upc might be set to None
        # TODO: Move this check to the CSVRows model. We should filter all bad
        # data out there. This Importer should only take sanitized data and
        # save it to Redis.
        if upc:
            # store upc in redis set
            self.inventory.add_item(upc, row)
